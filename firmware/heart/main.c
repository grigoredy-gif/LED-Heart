/*
 * LED heart board: beating heart firmware (STM8S003F3, SDCC)
 *
 * Buttons (top to bottom):
 *   MODE    not used here: the place to add your own animations (see run())
 *   SPEED   slow / normal / fast / faster
 *   DIM     darker (6 steps)
 *   BRIGHT  brighter
 *   ON/OFF  off (the chip sleeps, about 10 uA); hold it 0.5 s to switch on
 * It switches itself off 30 minutes after the last button press.
 * Speed and brightness are kept in EEPROM (saved 3 s after a change).
 *
 * Circuit (docs/design-notes.md, "Circuit" and the firmware notes):
 *   columns 1..9 (anodes, high = on): PD3 PD2 PC7 PC6 PC5 PC4 PC3 PA3 PD4
 *   rows 1..8: S8050 driven by 74HC595 QA..QH (high = on)
 *   595: SER = PD5, SRCLK and RCLK tied = PD6
 *   buttons, low = pressed: MODE PA1, SPEED PA2, DIM PD1 (= SWIM), BRIGHT PB4,
 *   ON/OFF PB5 (wakes the chip from halt)
 *
 * DIM shares its pin with SWIM: this firmware turns SWIM off to read it.
 * Flashing still works because the ST-Link resets the chip through RST first.
 */
#include <stdint.h>

#define REG(a) (*(volatile uint8_t *)(a))

#define PA_ODR REG(0x5000)
#define PA_IDR REG(0x5001)
#define PA_DDR REG(0x5002)
#define PA_CR1 REG(0x5003)
#define PB_IDR REG(0x5006)
#define PB_CR2 REG(0x5009)
#define PC_ODR REG(0x500A)
#define PC_DDR REG(0x500C)
#define PC_CR1 REG(0x500D)
#define PD_ODR REG(0x500F)
#define PD_IDR REG(0x5010)
#define PD_DDR REG(0x5011)
#define PD_CR1 REG(0x5012)
#define PD_CR2 REG(0x5013)
#define FLASH_CR2 REG(0x505B)
#define FLASH_NCR2 REG(0x505C)
#define FLASH_IAPSR REG(0x505F)
#define FLASH_DUKR REG(0x5064)
#define EXTI_CR1 REG(0x50A0)
#define CLK_CKDIVR REG(0x50C6)
#define TIM4_CR1 REG(0x5340)
#define TIM4_IER REG(0x5343)
#define TIM4_SR REG(0x5344)
#define TIM4_CNTR REG(0x5346)
#define TIM4_PSCR REG(0x5347)
#define TIM4_ARR REG(0x5348)
#define CFG_GCR REG(0x7F60)
#define EEPROM ((volatile uint8_t *)0x4000)

#define PA_COLS 0x08 /* PA3 */
#define PC_COLS 0xF8 /* PC3..PC7 */
#define PD_COLS 0x1C /* PD2, PD3, PD4 */
#define SER 0x20     /* PD5 */
#define SCK 0x40     /* PD6 */

#define B_MODE 0x01
#define B_SPEED 0x02
#define B_DIM 0x04
#define B_BRIGHT 0x08
#define B_ONOFF 0x10

#define AUTO_OFF_S 1800u

/* ---------------------------------------------------------------- display */

/* one 9-bit word per row (0 = top), bit 0 = column 1 (left) */
static volatile uint16_t fb[8];
static volatile uint16_t ms;  /* counts milliseconds */
static volatile uint16_t sec; /* counts seconds */
static volatile uint8_t blank;
static volatile uint8_t ontime = 11; /* sixteenths of the row time */
static uint8_t row, sub;
static uint16_t msub;

static const uint8_t levels[6] = {1, 2, 4, 7, 11, 16};
static const uint8_t speedmul[4] = {6, 4, 3, 2}; /* quarters */

static void clock595(uint8_t ser)
{
    if (ser)
        PD_ODR |= SER;
    else
        PD_ODR &= (uint8_t)~SER;
    PD_ODR |= SCK;
    __asm__("nop");
    __asm__("nop");
    PD_ODR &= (uint8_t)~SCK;
}

static void columns_off(void)
{
    PA_ODR &= (uint8_t)~PA_COLS;
    PC_ODR &= (uint8_t)~PC_COLS;
    PD_ODR &= (uint8_t)~PD_COLS;
}

static void columns_on(uint16_t b)
{
    uint8_t a = 0, c = 0, d = 0;
    if (b & 0x001) d |= 0x08; /* col 1 PD3 */
    if (b & 0x002) d |= 0x04; /* col 2 PD2 */
    if (b & 0x004) c |= 0x80; /* col 3 PC7 */
    if (b & 0x008) c |= 0x40; /* col 4 PC6 */
    if (b & 0x010) c |= 0x20; /* col 5 PC5 */
    if (b & 0x020) c |= 0x10; /* col 6 PC4 */
    if (b & 0x040) c |= 0x08; /* col 7 PC3 */
    if (b & 0x080) a |= 0x08; /* col 8 PA3 */
    if (b & 0x100) d |= 0x10; /* col 9 PD4 */
    PA_ODR |= a;
    PC_ODR |= c;
    PD_ODR |= d;
}

/* 595 empty (9 clocks with SER low), then one 1 in for row 1 */
static void start595(void)
{
    uint8_t i;
    for (i = 0; i < 9; i++)
        clock595(0);
    clock595(1);
    row = 0;
    sub = 0;
}

/* 16 kHz: 16 steps per row, 8 rows -> 125 frames per second.
   Step 0 changes the row; the columns go off after `ontime` steps.
   The 595's two clocks are tied, so its outputs are one clock late. */
void tim4_isr(void) __interrupt(23)
{
    TIM4_SR = 0;
    if (sub == 0) {
        uint8_t i;
        columns_off();
        clock595(row == 7); /* the clock that brings up row 8 feeds the next 1 */
        for (i = 0; i < 20; i++) /* about 5 us: the old row switches off */
            __asm__("nop");
        if (!blank)
            columns_on(fb[row]);
        row = (row + 1) & 7;
        ms++;
        if (++msub >= 1000) {
            msub = 0;
            sec++;
        }
    } else if (sub == ontime) {
        columns_off();
    }
    sub = (sub + 1) & 15;
}

/* wakes the chip from halt (ON/OFF on PB5) */
void portb_isr(void) __interrupt(4)
{
}

static uint16_t now(void)
{
    uint16_t t;
    __asm__("sim");
    t = ms;
    __asm__("rim");
    return t;
}

static uint16_t seconds(void)
{
    uint16_t t;
    __asm__("sim");
    t = sec;
    __asm__("rim");
    return t;
}

static void timer_start(void)
{
    TIM4_PSCR = 3;  /* 16 MHz / 8 = 2 MHz */
    TIM4_ARR = 124; /* / 125 = 16 kHz */
    TIM4_CNTR = 0;
    TIM4_SR = 0;
    TIM4_IER = 1;
    TIM4_CR1 = 1;
}

/* rough delay without the timer (only used while switched off) */
static void busy_ms(uint16_t n)
{
    uint16_t i;
    while (n--)
        for (i = 0; i < 1600; i++)
            __asm__("nop");
}

/* ------------------------------------------------------- settings, buttons */

static uint8_t speed = 1, bright = 4;
static uint8_t abort_anim, want_off, dirty;
static uint16_t dirty_at, last_press;
static uint8_t db_raw, db_cnt, stable;

static uint8_t buttons(void)
{
    uint8_t b = 0;
    if (!(PA_IDR & 0x02)) b |= B_MODE;   /* PA1 */
    if (!(PA_IDR & 0x04)) b |= B_SPEED;  /* PA2 */
    if (!(PD_IDR & 0x02)) b |= B_DIM;    /* PD1 */
    if (!(PB_IDR & 0x10)) b |= B_BRIGHT; /* PB4 */
    if (!(PB_IDR & 0x20)) b |= B_ONOFF;  /* PB5 */
    return b;
}

/* EEPROM bytes: 0 mode (unused here), 1 speed, 2 brightness, 3 check */
static void eeprom_load(void)
{
    uint8_t m = EEPROM[0], s = EEPROM[1], b = EEPROM[2], c = EEPROM[3];
    if (c == (uint8_t)(m ^ s ^ b ^ 0x5A) && s < 4 && b < 6) {
        speed = s;
        bright = b;
    }
    ontime = levels[bright];
}

/* One 4-byte word: the CPU stops for about 6 ms, so the LEDs go dark first. */
static void eeprom_save(void)
{
    uint16_t t = now();
    blank = 1;
    while ((uint16_t)(now() - t) < 2)
        ;
    FLASH_DUKR = 0xAE;
    FLASH_DUKR = 0x56;
    while (!(FLASH_IAPSR & 0x08))
        ;
    FLASH_CR2 = 0x40; /* word programming */
    FLASH_NCR2 = 0xBF;
    EEPROM[0] = 0;
    EEPROM[1] = speed;
    EEPROM[2] = bright;
    EEPROM[3] = (uint8_t)(speed ^ bright ^ 0x5A);
    while (!(FLASH_IAPSR & 0x04))
        ;
    FLASH_IAPSR &= (uint8_t)~0x08;
    blank = 0;
    dirty = 0;
}

static void changed(void)
{
    dirty = 1;
    dirty_at = now();
}

static void on_press(uint8_t p)
{
    last_press = seconds();
    /* MODE (p & B_MODE) is free: add a mode variable and use it in run() */
    if (p & B_SPEED) {
        speed = (speed + 1) & 3;
        changed();
    }
    if ((p & B_DIM) && bright > 0) {
        bright--;
        ontime = levels[bright];
        changed();
    }
    if ((p & B_BRIGHT) && bright < 5) {
        bright++;
        ontime = levels[bright];
        changed();
    }
    if (p & B_ONOFF) {
        want_off = 1;
        abort_anim = 1;
    }
}

/* called once per millisecond: debounce (20 ms), save, auto-off */
static void poll(void)
{
    uint8_t raw = buttons();
    if (raw != db_raw) {
        db_raw = raw;
        db_cnt = 0;
    } else if (db_cnt < 20 && ++db_cnt == 20) {
        uint8_t p = raw & (uint8_t)~stable;
        stable = raw;
        if (p)
            on_press(p);
    }
    if (dirty && (uint16_t)(now() - dirty_at) > 3000)
        eeprom_save();
    if ((uint16_t)(seconds() - last_press) >= AUTO_OFF_S) {
        want_off = 1;
        abort_anim = 1;
    }
}

/* wait t ms (scaled by the speed); returns 1 if the animation must stop */
static uint8_t pause(uint16_t t)
{
    uint16_t start, last, n;
    t = (uint16_t)(t * speedmul[speed]) >> 2;
    start = last = now();
    while (!abort_anim) {
        n = now();
        if (n != last) {
            last = n;
            poll();
        }
        if ((uint16_t)(n - start) >= t)
            break;
    }
    return abort_anim;
}

static void power_off(void)
{
    uint16_t i;
    if (dirty)
        eeprom_save();
    TIM4_IER = 0;
    TIM4_CR1 = 0;
    columns_off();
    for (i = 0; i < 9; i++)
        clock595(0);
    PD_ODR &= (uint8_t)~(SER | SCK);

    for (;;) {
        do /* all buttons released, plus 50 ms */
            busy_ms(50);
        while (buttons());
        __asm__("sim");
        EXTI_CR1 = (EXTI_CR1 & 0xF3) | 0x08; /* port B: falling edge only */
        PB_CR2 = 0x20;                       /* interrupt on PB5 only */
        __asm__("rim");
        __asm__("halt");
        PB_CR2 = 0;
        for (i = 0; i < 500; i++) { /* on only after a 0.5 s press */
            busy_ms(1);
            if (!(buttons() & B_ONOFF))
                break;
        }
        if (i == 500)
            break;
    }

    for (i = 0; i < 8; i++)
        fb[i] = 0;
    start595();
    timer_start();
    stable = db_raw = buttons();
    db_cnt = 20;
    last_press = seconds();
    want_off = 0;
    abort_anim = 1;
}

/* ------------------------------------------------------------ animation */

static const uint16_t heart_big[8] = {0x0C6, 0x1EF, 0x1FF, 0x1FF, 0x0FE, 0x07C, 0x038, 0x010};
static const uint16_t heart_small[8] = {0x000, 0x06C, 0x0FE, 0x0FE, 0x07C, 0x038, 0x010, 0x000};

static void show(const uint16_t *p)
{
    uint8_t r;
    for (r = 0; r < 8; r++)
        fb[r] = p[r];
}

/* one heartbeat: big, small, big, small and a rest */
static void beat(void)
{
    show(heart_big);
    if (pause(130)) return;
    show(heart_small);
    if (pause(110)) return;
    show(heart_big);
    if (pause(150)) return;
    show(heart_small);
    pause(550);
}

static void run(void)
{
    beat();
}

/* ------------------------------------------------------------------ main */

void main(void)
{
    CLK_CKDIVR = 0; /* 16 MHz */

    /* 595 lines first: outputs, low, fast; then clear the 595 */
    PD_ODR &= (uint8_t)~(SER | SCK);
    PD_DDR |= SER | SCK;
    PD_CR1 |= SER | SCK;
    PD_CR2 |= SER | SCK;
    start595();

    /* only now the columns: push-pull outputs, low */
    columns_off();
    PA_DDR |= PA_COLS;
    PA_CR1 |= PA_COLS;
    PC_DDR |= PC_COLS;
    PC_CR1 |= PC_COLS;
    PD_DDR |= PD_COLS;
    PD_CR1 |= PD_COLS;

    /* buttons: pull-ups on PA1, PA2, PD1 (PB4, PB5 have R18, R19);
       then SWIM off so that PD1 (DIM) reads as a normal input */
    PA_CR1 |= 0x06;
    PD_CR1 |= 0x02;
    CFG_GCR |= 0x01;

    eeprom_load();
    stable = db_raw = buttons();
    db_cnt = 20;
    timer_start();
    __asm__("rim");

    for (;;) {
        if (want_off)
            power_off();
        abort_anim = 0;
        run();
    }
}

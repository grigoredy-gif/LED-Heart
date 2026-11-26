/*
 * LED heart board: bring-up test (STM8S003F3, SDCC)
 *
 * What it does, over and over:
 *   1. lights the 72 LEDs one at a time, row by row from the top left
 *      (0.2 s each, about 15 s in all);
 *   2. lights every LED for 2 s;
 *   3. shows the heart for 3 s.
 * While MODE, SPEED, BRIGHT or ON/OFF is held, the whole column 1, 2, 4 or 5
 * lights instead (DIM is not read: its pin is the programming pin SWIM, and
 * this test leaves SWIM working so the board can always be flashed again).
 *
 * Reading the result: a dark dot = that LED or its joint; a dark row = its
 * transistor, base resistor or the 595; a dark column = its 270 ohm resistor
 * or the STM8 pin; two dots lit at once = a solder bridge.
 *
 * Circuit (docs/design-notes.md, "Circuit"):
 *   columns 1..9 (anodes, high = on): PD3 PD2 PC7 PC6 PC5 PC4 PC3 PA3 PD4
 *   rows 1..8 (cathodes): S8050 driven by 74HC595 QA..QH, high = on
 *   595: SER = PD5, SRCLK and RCLK tied = PD6, OE low, SRCLR high
 *   buttons (low = pressed): MODE PA1, SPEED PA2, DIM PD1, BRIGHT PB4, ON/OFF PB5
 */
#include <stdint.h>

#define REG(a) (*(volatile uint8_t *)(a))

#define PA_ODR REG(0x5000)
#define PA_IDR REG(0x5001)
#define PA_DDR REG(0x5002)
#define PA_CR1 REG(0x5003)
#define PA_CR2 REG(0x5004)
#define PB_IDR REG(0x5006)
#define PC_ODR REG(0x500A)
#define PC_DDR REG(0x500C)
#define PC_CR1 REG(0x500D)
#define PD_ODR REG(0x500F)
#define PD_DDR REG(0x5011)
#define PD_CR1 REG(0x5012)
#define PD_CR2 REG(0x5013)
#define CLK_CKDIVR REG(0x50C6)
#define TIM4_CR1 REG(0x5340)
#define TIM4_IER REG(0x5343)
#define TIM4_SR REG(0x5344)
#define TIM4_PSCR REG(0x5347)
#define TIM4_ARR REG(0x5348)

/* column pins on each port */
#define PA_COLS 0x08 /* PA3 */
#define PC_COLS 0xF8 /* PC3..PC7 */
#define PD_COLS 0x1C /* PD2, PD3, PD4 */
#define SER 0x20     /* PD5 */
#define SCK 0x40     /* PD6 */

/* one 9-bit word per row, bit 0 = column 1 (left) */
static volatile uint16_t fb[8];
static volatile uint8_t held_col; /* 0 = no button held, else column to light */
static volatile uint16_t ms;
static uint8_t row; /* row the next tick shows, 0 = top */

static const uint16_t heart[8] = {
    /* .##...##.  ####.####  #########  #########
       .#######.  ..#####..  ...###...  ....#.... */
    0x0C6, 0x1EF, 0x1FF, 0x1FF, 0x0FE, 0x07C, 0x038, 0x010};

static void short_wait(void) /* about 2.5 us at 16 MHz */
{
    uint8_t i;
    for (i = 0; i < 10; i++)
        __asm__("nop");
}

/* One clock of the 595. The two clocks are tied, so the outputs show what the
   shift register held before this clock. SER and SCK change in separate
   writes. */
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

/* 1 ms tick: next row. 8 rows -> 125 frames per second. */
void tim4_isr(void) __interrupt(23)
{
    uint16_t b;
    TIM4_SR = 0;
    columns_off();
    /* the clock that brings up row 8 feeds the next 1 in, for row 1 */
    clock595(row == 7);
    short_wait(); /* let the old row's transistor switch off */
    b = held_col ? (uint16_t)(1u << (held_col - 1)) : fb[row];
    columns_on(b);
    row = (row + 1) & 7;
    ms++;
}

static uint16_t now(void)
{
    uint16_t t;
    __asm__("sim");
    t = ms;
    __asm__("rim");
    return t;
}

static void read_buttons(void)
{
    uint8_t col = 0;
    if (!(PA_IDR & 0x02)) col = 1;      /* MODE   PA1 */
    else if (!(PA_IDR & 0x04)) col = 2; /* SPEED  PA2 */
    else if (!(PB_IDR & 0x10)) col = 4; /* BRIGHT PB4 */
    else if (!(PB_IDR & 0x20)) col = 5; /* ON/OFF PB5 */
    held_col = col;
}

static void wait_ms(uint16_t n)
{
    uint16_t start = now();
    while ((uint16_t)(now() - start) < n)
        read_buttons();
}

static void show(const uint16_t *p)
{
    uint8_t r;
    for (r = 0; r < 8; r++)
        fb[r] = p ? p[r] : 0;
}

void main(void)
{
    uint8_t r, c;

    CLK_CKDIVR = 0; /* 16 MHz */

    /* 595 lines first: outputs, low, fast */
    PD_ODR &= (uint8_t)~(SER | SCK);
    PD_DDR |= SER | SCK;
    PD_CR1 |= SER | SCK;
    PD_CR2 |= SER | SCK;

    /* clear the 595 (9 clocks with SER low), then put one 1 in for row 1 */
    for (c = 0; c < 9; c++)
        clock595(0);
    clock595(1);
    row = 0;

    /* only now the columns: push-pull outputs, low */
    columns_off();
    PA_DDR |= PA_COLS;
    PA_CR1 |= PA_COLS;
    PC_DDR |= PC_COLS;
    PC_CR1 |= PC_COLS;
    PD_DDR |= PD_COLS;
    PD_CR1 |= PD_COLS;

    /* buttons: PA1, PA2 inputs with pull-up; PB4, PB5 have R18, R19 */
    PA_CR1 |= 0x06;

    /* TIM4: 16 MHz / 64 / 250 = 1 kHz */
    TIM4_PSCR = 6;
    TIM4_ARR = 249;
    TIM4_SR = 0;
    TIM4_IER = 1;
    TIM4_CR1 = 1;
    __asm__("rim");

    for (;;) {
        /* 1. one LED at a time */
        for (r = 0; r < 8; r++) {
            for (c = 0; c < 9; c++) {
                show(0);
                fb[r] = (uint16_t)(1u << c);
                wait_ms(200);
            }
        }
        /* 2. all on */
        for (r = 0; r < 8; r++)
            fb[r] = 0x1FF;
        wait_ms(2000);
        /* 3. heart */
        show(heart);
        wait_ms(3000);
    }
}

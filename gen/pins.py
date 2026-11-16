"""
pins.py - the two free choices of the LED heart board, shared by the schematic, the check and the board scripts.
The firmware needs the same two tables.
"""
# matrix column (1 = left ... 9 = right) -> pin of U1 (STM8S003F3P6, TSSOP-20)
COLPIN = {1: 20, 2: 19, 3: 17, 4: 16, 5: 15, 6: 14, 7: 13, 8: 10, 9: 1}
PINNAME = {1: "PD4", 10: "PA3", 13: "PC3", 14: "PC4", 15: "PC5", 16: "PC6", 17: "PC7", 19: "PD2", 20: "PD3"}
# matrix row (1 = top ... 8 = bottom) -> output pin of U2 (74HC595: 15 = QA, 1 to 7 = QB to QH)
ROWOUT = {1: 15, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7}
# the buttons from top to bottom: (reference, port pin, U1 pin, name printed on the board)
# ON/OFF must be on a pin that can wake the chip from halt. PA1 cannot (ST data sheet, table 6, note 2:
# "PA1 ... cannot be used for waking up the device"), so the top button is MODE and the bottom one ON/OFF.
BUTTONS = [("SW1", "PA1", 5, "MODE"), ("SW2", "PA2", 6, "SPEED"), ("SW3", "PD1", 18, "DIM"),
           ("SW4", "PB4", 12, "BRIGHT"), ("SW5", "PB5", 11, "ON/OFF")]

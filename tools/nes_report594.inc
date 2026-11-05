/* Generated dictionary and bound cover only immutable compiled report formats.
 * Stack lifetime ends before the report returns to file I/O. */
#include <stdarg.h>
int nes_report594(char *text, size_t capacity, const unsigned char *encoded, ...) {
 static const char words[] = WORDS594;
 static const uint16_t offsets[] = { OFFSETS594 };
 char format[CAP594];
 char *next = format;
 while (*encoded) {
  unsigned symbol = *encoded++;
  if (symbol < 128) {
   *next++ = (char)symbol;
  } else {
   const char *word = words + offsets[symbol-128];
   while (*word) *next++ = *word++;
  }
 }
 *next = 0;
 va_list args;
 va_start(args, encoded);
 int used = vsnprintf(text, capacity, format, args);
 va_end(args);
 return used;
}

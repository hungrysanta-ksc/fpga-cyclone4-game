/* SPDX-License-Identifier: MIT */
#ifndef MCU_LOADER_PLATFORM_H
#define MCU_LOADER_PLATFORM_H
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
typedef unsigned UINT;
typedef unsigned FRESULT;
typedef uint32_t tick_t;
typedef struct {unsigned fsize,pos;} FIL;
typedef struct {uint32_t MODER,ODR,IDR;} MockGPIO;
typedef struct {uint32_t SR,CR1;} MockSPI;
extern MockGPIO mock_a,mock_b;
extern MockSPI mock_spi;
extern FRESULT file_res;
extern const uint8_t *fpga_config;
#define GPIOA (&mock_a)
#define GPIOB (&mock_b)
#define SPI1 (&mock_spi)
#define FPGA_SSREG GPIOA
#define FPGA_SSBIT 4
#define SPI_CR1_SPE 64u
#define SPI_SR_BSY 128u
#define SPI_SR_TXE 2u
#define FPGA_BASE ((const uint8_t *)"/sd2snes/fpga_base.bi3")
#define FPGA_TEST_TOKEN 0xa5
#define OTG_FS_IRQn 67
#define FR_OK 0u
#define FA_READ 1u
#define FA_WRITE 2u
#define FA_CREATE_ALWAYS 8u
#define f_size(f) ((f)->fsize)
void mock_pin(MockGPIO *,unsigned,bool);
#define SET_BIT(p,b) mock_pin(p,b,true)
#define CLEAR_BIT(p,b) mock_pin(p,b,false)
unsigned NVIC_GetEnableIRQ(int);
void NVIC_DisableIRQ(int);
void NVIC_EnableIRQ(int);
void snes_reset(int);
int get_snes_reset(void);
void delay_us(unsigned);
void delay_ms(unsigned);
tick_t getticks(void);
void fpga_pgm(uint8_t *);
unsigned fpga_test(void);
FRESULT f_open(FIL *,const char *,unsigned);
FRESULT f_read(FIL *,void *,UINT,UINT *);
FRESULT f_write(FIL *,const void *,UINT,UINT *);
FRESULT f_close(FIL *);
FRESULT f_lseek(FIL *,uint32_t);
#endif

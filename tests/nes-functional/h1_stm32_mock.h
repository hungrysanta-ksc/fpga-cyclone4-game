/* SPDX-License-Identifier: MIT */
#ifndef H1_STM32_MOCK_H
#define H1_STM32_MOCK_H
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
typedef struct {uint32_t MODER,ODR,IDR;} mock_gpio;
typedef struct {uint32_t CR1,SR;} mock_spi;
extern mock_gpio port_a,port_b;
extern mock_spi spi_1;
#define GPIOB (&port_b)
#define FPGA_SSREG (&port_a)
#define FPGA_SSBIT 4
#define SPI1 (&spi_1)
#define SPI_SR_BSY (1u<<7)
#define SPI_SR_TXE (1u<<1)
#define SPI_CR1_SPE (1u<<6)
#define FR_OK 0
#define FPGA_BASE ((const uint8_t *)"/sd2snes/fpga_base.bi3")
#define FPGA_TEST_TOKEN 0xa5
extern unsigned file_res;
extern const uint8_t *fpga_config;
#define OTG_FS_IRQn 67
unsigned NVIC_GetEnableIRQ(int);
void NVIC_DisableIRQ(int);
void NVIC_EnableIRQ(int);
void pin_write(mock_gpio *,unsigned,bool);
#define SET_BIT(p,b) pin_write(p,b,true)
#define CLEAR_BIT(p,b) pin_write(p,b,false)
void delay_us(unsigned);
void delay_ms(unsigned);
void snes_reset(unsigned);
unsigned get_snes_reset(void);
void fpga_pgm(uint8_t *);
int fpga_get_done(void);
unsigned fpga_test(void);
#endif

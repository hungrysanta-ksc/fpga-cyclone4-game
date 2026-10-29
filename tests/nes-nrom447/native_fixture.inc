static bool native_session165(const struct nes_rom_spi_io *io,uint32_t epoch){
 uint8_t image[162]={4,0};memcpy(image+2,chr,160);rpc(4,0,image,162,NULL,0);
 if(!observe136(io,&nes_run136.first))return false;
 for(unsigned i=0;!nes_run136.first&&i<100;i++)if(!observe136(io,&nes_run136.first))return false;
 if(!nes_runtime165_begin(&runtime,&received,&video,native_palette165,transfer,ticks,service,NULL,1000000,&resident,epoch,true))return false;
 while(!runtime.frames&&nes_runtime165_step(&runtime))if(++steps>=2000)return false;
 if(runtime.result||runtime.frames!=1||received.state!=NES_NATIVE165_IDLE||qacks!=1||retired!=1||!tokens)return false;
 if(!observe136(io,&nes_run136.last))return false;return true;
}

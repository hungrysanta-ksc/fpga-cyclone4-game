"""Widen the MMC1012 load/check/run memory path for the isolated Kirby profile."""
import argparse
import hashlib
from pathlib import Path
import shutil
from cross_nes1022 import rom_path

FILES=("nes_rom_boot","nes_rom_loader","nes_rom_spi","nes_spi_boot","nes_source_epoch207","nes_live_joint","nes_probe","cart_nrom")

BASE_HASHES={
    "nes_rom_boot": "12cad349ecd8903dec87006a5e8fa8f183e2af278b92da288c4e286f5ff6178f",
    "nes_rom_loader": "d323f74be750bdb97a43d90a91f2597d17bf1908295a09b171c410223cd0fc2c",
    "nes_rom_spi": "7d48d24fd734422f95347148a37c8173abd8d743b3f537e4405f325d863db2dc",
    "nes_spi_boot": "8ea65b8b3658e334981b4c29a4d79ca4e6db68a5743f6d0702e95e290c0e3a63",
    "nes_source_epoch207": "8c0a4183991c125123c1bc7bb171197f2a1346be7316841859b8e359e48d1217",
    "nes_live_joint": "987fd646e2d94557fc5e38ae2242cafe5062b9f0c53b236148abae203719c34c",
    "nes_probe": "dd6e97f186be2d18afba8fd19d9da8c73d1fda71ae8f11dfbc67ee5ae3145cd2",
    "cart_nrom": "b2d8d71f05a0e1934a27ffc19bd83d6fb03c33fa26099960f667164911b944d9",
    "nes_rom_physical": "d93515e5a3bc6014cf3782c0dc4686c65a11207974315d51551a0448414cc6de"
}


def patch(name,s):
    if name in FILES[:6]:
        # All [18:0] fields in these boot/controller modules are loader counts or CHECK tags.
        if name=="nes_live_joint":
            s=s.replace("[18:0] out_loaded_bytes","[19:0] out_loaded_bytes").replace("[18:0] loaded_bytes","[19:0] loaded_bytes")
        else:
            s=s.replace("[18:0]","[19:0]")
        s=s.replace("19'h60000","20'hc0000")
    if name=="nes_rom_loader":
        s=s.replace("loaded_bytes[18]?","loaded_bytes[19]?").replace("{4'd0,loaded_bytes[17:0]}","{3'd0,loaded_bytes[18:0]}").replace("{3'd0,loaded_bytes}","{2'd0,loaded_bytes}")
        anchor="loaded_bytes[18]<=loaded_bytes[18] ^ (&loaded_bytes[17:0]);"
        assert s.count(anchor)==1
        s=s.replace(anchor,anchor+"\n    loaded_bytes[19]<=loaded_bytes[19] ^ (&loaded_bytes[18:0]);")
    if name=="nes_rom_boot":
        s=s.replace("a[21:17]==5'h10","a[21:18]==4'h8").replace("check_address[18] ?","check_address[19] ?")
        s=s.replace("1'b1,3'b0,check_address[17:0]","1'b1,2'b0,check_address[18:0]").replace("3'b0,check_address}","2'b0,check_address}")
        s=s.replace("raw_check_address[21],raw_check_address[17:0]","raw_check_address[21],raw_check_address[18:0]")
    if name=="nes_rom_spi":
        s=s.replace("8'h7b","8'h7c").replace("5'd0,check_next","4'd0,check_next").replace("5'd0,loaded_bytes","4'd0,loaded_bytes").replace("loaded_bytes[18:12]","loaded_bytes[19:12]")
        anchor="check_next[18]<=check_next[18] ^ (next_carry8 && (&check_next[17:8]));"
        assert s.count(anchor)==1
        s=s.replace(anchor,anchor+"\n        check_next[19]<=check_next[19] ^ (next_carry8 && (&check_next[18:8]));")
    if name=="nes_probe":
        s=s.replace("21'h03ffff","21'h07ffff").replace("20'h1ffff","20'h3ffff")
    if name=="cart_nrom":
        s=s.replace("32'h00004004","32'd4")
    return s


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ("board","rom_dir","output"):
        ap.add_argument(k,type=Path)
    a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    for n,digest in BASE_HASHES.items():
        assert hashlib.sha256((a.board/(n+".sv")).read_bytes()).hexdigest()==digest,n
    for n in FILES:
        f=a.board/(n+".sv")
        orig=f.read_text()
        new=patch(n,orig)
        assert orig!=new,n
        (a.output/f.name).write_text(new)
    shutil.copyfile(a.board/"nes_rom_physical.sv",a.output/"nes_rom_physical.sv")
    (a.output/"payload.bin").write_bytes(rom_path(a.rom_dir,"kirby").read_bytes()[16:])

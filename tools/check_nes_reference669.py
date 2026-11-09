"""Pin the sd2snes+ review and selected MMC666 inputs; no timing simulation."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '6867510aba14693543577a87fa161595e1422b42'
UPSTREAM = {
    'verilog/sd2snes_nes/nes_bridge.v': '3f835edcc06a5fa0b3dc52db2a6af988765a040b',
    'snes/nes/nes_transport_device.a65': 'b10533927b34e66e93dcfaf7c1c74efd7c13f061',
    'snes/nes/nes_render.a65': '0393c501dc3bb484ddba8d4a47f581334430affb',
    'src/nes.c': 'f3f187d3d3328c8141b85cc707ac18e611e4caaa',
    'src/nes_chr.c': '275fc0b3b3f72f90acd04598819da037de1b84ef',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def audit(a):
    upstream = {}
    for name, expected in UPSTREAM.items():
        path = a.reference / name
        if not path.exists() and name == 'verilog/sd2snes_nes/nes_bridge.v':
            path = a.reference / 'nes_bridge.v'  # preserved 658 source subset
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert blob == expected, (name, blob, expected)
        upstream[name] = dict(bytes=len(data), git_blob=blob, SHA256=sha(path),
            url=f'https://github.com/ludufre/sd2snes/blob/{COMMIT}/{name}')
    old = read(ROOT / 'analysis/reference658-verification.json')
    assets = {}
    for name, expected in old['assets'].items():
        path = a.distribution / name
        assert sha(path) == expected['sha256'] and path.stat().st_size == expected['bytes'], name
        assets[name] = expected
    package = read(ROOT / 'analysis/trial666-package.json')
    selected = read(ROOT / 'analysis/entry665-verification.json')
    assert sha(a.arm / 'obj-nes-100/firmware.stm') == package['firmware_SHA256']
    assert sha(a.client / 'sink165.sfc') == selected['client_SHA256']
    manifest = read(a.board / 'inputs665.json')
    assert all(sha(a.board / name) == expected for name, expected in manifest['inputs'].items())
    board = selected['boards']['entry665']
    assert all(sha(a.board / 'output_files' / name) == expected
               for name, expected in board['timing']['pins'].items())
    files = {name: sha(a.board / name) for name in (
        'board.qsf', 'fxpak_nes_screen137_top.sv', 'nes_sink_spi165.sv',
        'nes_sink_bridge165.sv', 'nes_tile_bulk206.sv', 'nes_bulk_aperture188.sv')}
    result = dict(review=669, scope='Source/artifact identity audit and plan review only',
        upstream_commit=COMMIT, upstream_files=upstream, distribution=assets,
        selected='MMC666', firmware_SHA256=package['firmware_SHA256'],
        client_SHA256=selected['client_SHA256'], board_inputs_checked=len(manifest['inputs']),
        board_sources=files, ARM_sources={name: sha(a.arm / name) for name in (
            'nes_native_sink165.c', 'nes_sink_window184.c')},
        resources=dict(LE=board['LE'], LAB=board['LAB'], M9K=board['M9K'],
            Flash_B=package['Flash_B'], Flash_free_B=package['Flash_free_B'],
            reference_mailbox_B=16384, existing_bulk_B=4096, existing_packet_queue_B=1024,
            existing_storage_is_not_free=True),
        dispositions=dict(
            CHR_preconversion='adapted660_661_selected',
            small_PSRAM_to_VRAM_DMA='rejected659_with_ROM_contention',
            FPGA_to_SNES_map_stream='remaining_budget_gate_before_implementation',
            active_display_WRAM_DMA='already_present; reconsider ownership/scheduling, not new DMA',
            scanline_work_budget='remaining_bounded_comparison',
            ACK_before_display_and_error_ACK='not_adopted; keep independent final display ACK'),
        new_simulation=False, new_synthesis=False, speedup_measured=False, new_delivery=False,
        evidence={name: sha(ROOT / 'analysis' / name) for name in (
            'reference658-verification.json', 'bg659-verification.json',
            'word660-verification.json', 'entry665-verification.json',
            'trial666-package.json', 'output668-verification.json')})
    a.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(source_files=len(upstream), distribution_files=len(assets),
        board_inputs=result['board_inputs_checked'], selected=result['selected'],
        new_simulation=False, new_synthesis=False)))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('reference', 'distribution', 'arm', 'client', 'board', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    audit(p.parse_args())

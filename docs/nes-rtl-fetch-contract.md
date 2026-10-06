# NES RTL CHR fetch 검증 계약

SPDX-License-Identifier: MIT.

`tools/nes_functional.py`와 FLOAT 래퍼는 RTL-006 그대로 사용한다. build.json의 candidate는 실행 인프라 버전 `NES-P2-RTL-006`, 이번 시험 결과는 `NES-P2-RTL-FETCH-007`이다. 기존 `tools/build_nes_fetch.py`로 만든 자체 NROM만 사용한다.

```powershell
& $PY -B -X utf8 tools/build_nes_fetch.py --out "$env:TEMP/nes-fetch-original"
& ./tools/run_nes_functional.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-rtl-fetch" -Diagnostic "$env:TEMP/nes-fetch-original" -Testbench tests/nes-functional/fetch_tb.sv
& $PY -B -X utf8 tools/verify_nes_rtl_fetch.py --run "$env:TEMP/nes-rtl-fetch" --mesen-reference analysis/local-fetch-verified/repeat
```

경로/실행 규칙은 [Questa 계약](questa-execution.md)과 전역 AGENTS.md를 따른다. 새 ASCII 출력 경로를 사용한다. Mesen 기록이 없으면 [FETCH-005 계약](nes-fetch-contract.md)으로 같은 ROM의 참조를 재생성한다.

- 메모리 응답은 1 master tick, reset 20µs, 총 140.02ms. 60ms 이후 첫 pre-render부터 연속 4프레임을 기록한다.
- 등록된 색 출력의 `cycle=x+2`(2..257)에서 256×240 전부를 비교한다. 강조색은 0이다.
- `ppu_ce` 상승 시 NBA 갱신 전 `bgp_en` 및 pattern latch 조건을 관측한다. BgPainter low/high latch cycle 6/8은 Mesen read slot 5/7과 대응한다. 메모리 strobe가 유지되는 동안 중복 거래로 세지 않는다.
- pre-render를 -1로 정규화한다. 프레임당 배경 latch 16,388건의 슬롯·물리 주소·CHR byte를 검사한다. 화면 화소에 쓰인 15,360건만 독립 좌표 oracle 및 Mesen 주소/값과 비교한다. 미사용 pre-render/right-edge fetch 값과 sprite dummy read 동등성은 검증하지 않는다.
- 패턴 테이블별 Mesen 참조 프레임을 매칭한다. 부팅 프레임 번호나 CPU/PPU 절대 위상을 같다고 가정하지 않는다. 고정 Mesen 팔레트로 변환한 전체 RGB bytes도 일치해야 한다.
- simulator 종료코드뿐 아니라 PASS marker, Fatal/Error 부재, 모든 수치와 참조 비교를 요구한다.
- Questa의 SV `%03d` 파일명은 공백으로 패딩된다(`frame-  1.hex`). 검증기는 실제 이름을 그대로 읽는다.

8KB CHR는 처음부터 상주한다. NROM PPUCTRL 전환 시험이며 MMC3 bank mapping, A12/IRQ, cache miss, 외부 메모리 지연, NES→SNES 출력, fit/STA 또는 실기 검증은 아니다.

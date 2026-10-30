# NES500 — A1의 PPU 수집 거부 경계 재현

2026-10-31. PR138 merge `7e9699fb5d3ce4617495c204aa04d194cb09798d`에 감사499 head가 포함됨을 확인하고 `codex/nes-capture-correctness-500`에서 시작했다. [새 계획](nes-audit499-plan.json) · [검증](../analysis/capture500-verification.json).

**실기493의 fetch01/04/06과 같은 세 오류 유형을 현재 PPU·수집기의 정상 렌더링 중단/재개 경계에서 재현했다.** A1의 원인 분리 단계이며, 수정·실기 성능 향상 또는 A1 전체 완료는 아니다. 정상493·ARM·65816·loader·STOP/ACK/메뉴 경로를 변경하지 않았다.

## 시험 연결과 범위

- 정상493과 byte동일한489 board02에서 PPU, frame201, planes165, compact181, raster181, patch capture/rows181 및save-state 지원9파일을 가져와493 제작hash와 대조했다. 새 source/core 후보를 섞지 않았다.
- 기존179 실제 SMB3 첫 레벨 기록의620/650/699 frame에서 PPUMASK 쓰기를 재생하고, $2006을 포함하는 조건과 제외하는 조건을 나눴다.0/1/3dot 지연과 정상 baseline을 합친19조건이다. 이어699의 나머지2/4/5/6/7dot을 검사해8dot 주기의 모든 위상을 확인했다. 주사선193은 기록된 시험 입력일 뿐 구현 예외 조건이 아니다.
- PPU는 그대로 실행하고 CPU/mapper/PSRAM 대신 결정적인 always-ready VRAM 데이터를 공급했다. 따라서 ROM 경쟁·게임 전체 재생·실기 write 지연을 재현한 것은 아니다. 다른 PPU에서 기록한 write 시각이므로 위상 민감도로 해석한다.
- 실제PPU 출력은 독립적인 post-CE 관측기로 읽었다. raw RAM의 보존 픽셀과 비교했다. 이는 해당PPU의 raw 행 보존 증명이며 독립NES emulator의 전체 장면 또는SNES 출력 픽셀 증명은 아니다.
- 첫19조건은 정상13/거부6이었다. 모든18개 중단/재개 조건에서2개raw 행, 합계9216픽셀이 관측기와 정확히 일치했다. 상세추적3조건은 동일 결과를 확인했고 추가위상5조건은 별도 표로 기록했다. `completed`는 거부 동작까지 관측했다는 뜻이지 모든조건이정상표시됐다는뜻이아니다.
- 중복을제외한최종24조건은정상15/거부9다. 세fetch signature01/04/06을모두재현했고23개중단/재개조건의raw11776픽셀이일치했다. 이조건별거부비율은실기frame 거부율이아니다.

## 원인별 실제 사건

| 조건 | 관측된 원인 | 결과 |
|---|---|---|
| baseline | 중단 없는224행 | geometry valid, fetch0, raw0 |
| 620/+3dot | 193:22의low가pending으로남고194:8의high가도착. oldrow185/newrow186으로서로다른행 | fetch04 |
| 699/+0dot | 193:334에서low/load는1이나ROM read는0. 193:336에서high는도착하지만유효한low가없음 | fetch02 이후06 |
| 699/+1,+2dot | 재개 직후 유효한짝이없는high | fetch04 |
| 699/+5,+6dot | 이전행low가pending인데194:6에서다음행low가도착 | fetch01 |

PPU의 `native_bg_low/high`는 `bgp_en/rendering_enabled`의 실제pattern load 조건이다. ROM의read는 지연된`is_rendering_d`와read phase를 따른다. 재개 순간두조건이항상동시에유효하지않다. 기존planes는low/high를같은행에서완료되는한쌍으로가정하며, `pair_pending`은행완료가아니라frame reset/end와다음high에서정리한다.

그래서 **완전한raw 행이이미보존됐어도 planes의sticky fetch 오류가frame 전체를무효화**한다. `frame201`은fetch invalid를compact와raw capture의source fault로전파한다. 관측한실패의compact40/patch20은그전파와일치한다. $2006포함여부와관계없이해당PPUMASK 경계에서실패했으므로이번반례에서는중간주소쓰기만이필수원인은아니다.

이는실기01/04/06을설명할수있는실제RTL 메커니즘이다. 실기V3는first-error 위치를저장하지않으므로실기에서그세오류가모두이원인이라는증명은아니다. 반복거부의개수/손실ms/FPS회복량도산출하지않는다.

## 다음 수정의 정확한 경계

1. `planes165`의frame 단위불완전pair를행단위로분류한다. 현재raw capture의`row_commit/row_patched/committed_row`와연결하고,이전행pending을다음행의짝으로재사용하지않는다.
2. 실제render-off/restart 때문에생긴불완전fetch만해당행의raw coverage로대체할수있다. **raw slot이있다는사실만으로승인하지않고256픽셀완료·행identity·세대·최종patch valid까지요구**한다. pending 삭제만으로는다음orphan high가남으므로충분하지않다.
3. 데이터가유효한실제read의잘못된주소/lane/geometry, ROM data-invalid/rom_fault, missing pixel, raw capacity초과, 다른행/세대, STOP/중간취소는계속거부한다. 회복이허용되는‘read가발생하지않은중단구간’과실제버스오류를구분한다.
4. 마지막raw행완료와fetch owned/valid 공개사이에race가없어야한다. 유효성확정전query/export를열거나ROM fault를raw로숨기지않는다. 현재ARM/65816의독립검사·최종ACK·VBlank를유지한다.
5. 새framebuffer/ROM cache를추가하지않고기존raw RAM을재사용하는범위부터구현한다. 추가행상태/제어와기존pair 진행제어의대체를명시하고기능/반례통과뒤한번의전체Lite비용으로확인한다. 아직이수정의면적·시간예산이검증된것은아니다.

다음작업은A1의이수정과반례검증이다. A2 전송·DMA최적화,498 승격,새실기전달본으로건너뛰지않는다. 형식적인오류비트마스킹·게임명/고정주사선 예외·불완전픽셀을검정색으로대체하는수정은하지않는다.

## 재현·실패 보존

`tools/test_nes_capture500.py prepare --board <489-board02> --reference <179-reference05> --out <fresh-ASCII>`로입력을생성한다. `--focus`는조건명을쉼표로지정하고`--phase-sweep`는0..7dot을생성한다. 실제run은기존Questa Starter FLOAT wrapper의`-RunOnly -AfterSmokeScript <absolute job>`로한좌석에서순차실행했다. `-L altera_mf_ver`를사용한다. 새유료/복수라이선스는필요하지않았다.

선택은로컬`nes-capture500-test03`,상세`nes-capture500-trace01`,추가위상`nes-capture500-phase01`이다. `tools/analyze_nes_capture500.py`는각입력·source·stimulus·log hash와결과를확인해공개요약을생성한다. raw waveform/game ROM/license/server log는Git에넣지않는다.

- test01:현재PPU의Intel RAM library를빼먹어elaboration 실패. 동작결과없음.
- test02:fixture가ROM data-valid 대신PPU ALE/address-valid를연결해baseline부터06으로실패했다. 검사입력의의미를보드와대조해수정하고중단했다. 이결과는제품결함근거에서제외한다.
- test03부터baseline valid를필수조건으로삼았다. 실패/중단원시로그와기존493/498 자료는보존했다. sandbox의PC식별실패는허가된host wrapper로실행해해소했으며라이선스내용을변경하지않았다.

새Quartus·FPGA/ARM 바이너리·ZIP·실기측정은없다. 실기기준은계속493 평균9.57fps이며현재수집거부율과수정후속도는미측정이다.

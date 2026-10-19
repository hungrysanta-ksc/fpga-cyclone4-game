# NES259 — 실제 ARM serializer와 공유 SPI 비용

2026-10-19, PR130. Cortex-M4로 컴파일한 token 배정·4credit·serializer·H2 생성 코드를 실행하고 실제 출력 RTL에 연결했다. 기존 C 계획 71개는 일반 명령과 map 값, H2 인증서가 모두 일치했다. **작은 map 범위마다 패킷을 만드는 현재 구성은 시간 여유를 확보하지 못했다.** 회로 공유의 이득은 유지하지만 P2 제품 구현은 선택하지 않는다.

[실행 계획](nes-output259-plan.json) · [검증](../analysis/output259-verification.json) · [시간표](../analysis/output259-costs.csv) · [이전 경계](nes-mux258-contract.ko.md)

## 실제 실행 범위

`nes_output259.c`를 Cortex-M4/Thumb/soft-float/Os로 빌드하고 Unicorn에서 실제 명령을 실행한다. `io259` 경계에서 전송 버퍼를 Questa의 SPI 핀 구동기로 넘긴다. ARM에서 실제로 실행하는 것은 token 조회/예약, sequence/serial/generation 작성, queue credit 확인, 패킷 CRC, 일반 명령 직렬화, HDMA 의미 검사 및 H2 작성이다. 입력은 기존2472 C planner의 고정된 실제 출력이다. N5 복원기·화면 planner·STM32 SPI 드라이버·RUN/IRQ를 통째로 다시 실행한 결과가 아니다.

기존 op9는 실제 SNES의 packed-map 명령이었다. 새 typed 명령은 op12로 분리하고 H2는 op13으로 전달한다. 일반 패킷 header[1]은 section이며 typed 패킷만 bank로 검사한다. op1 BEGIN, op7 tile, op2 COPY, op4/5/8 fill, op10/11 manifest, op3 SEAL의 원래 payload를 유지한다. ARM은 기존 packed-map을 최대64B의 typed 범위로 분해한다.

기존 F7은 마지막 일반 ACK 내용을 돌려줬다. typed parser의 retire에는 일반 ACK가 없으므로 그 값으로 모든 완료를 추정할 수 없었다. F8/24B 상태는 accepted/retired16, tile 종료/준비/owner, next/head token32, 길이·bank·kind·slot·generation 및 CRC8을 원자적으로 snapshot한다. FPGA의 일반 ACK 검사기는 그대로 두고, 중복된96bit completed-ACK 보관만 제거했다. ARM은 수신 counter와 자신이 전송한 counter를 함께 검사해 최대4credit를 사용한다.

tile token은 FPGA에서 실제로 할당한 값을 조회해 명령에 넣는다. tile 종료와 마지막 chunk 소비 이후 next token을 읽고 map token을 순차 예약한다. FPGA는 각 OPEN에서 그 예약을 다시 확인한다. 느린 tile 시험에서 queue drain 완료가 곧 tile 준비 완료가 아님을 확인했다. 이를 고쳐 phase 준비를 최대256회 조회하며, 준비된 뒤의 길이/kind/slot/generation 불일치는 즉시 거부한다. 이 횟수는 제품의 wall-clock deadline을 정의한 것이 아니다. 오류 뒤에는 추가 SPI/SEAL을 발행하지 않는다. 재시작은 공통 STOP/reset 및 새 identity와 묶어야 한다.

## 일반 명령·DMA·검사

출력 시험은 실제 queue/ACK/parser, tile206 producer, 공유 aperture, CDC/token/receipt/final-ACK RTL을 사용한다. SNES 쪽은 명시적인 bus/service 시험 모델이다. 모델은 일반 packet을 실제 버스로 읽고 COPY/fill을 수행하며 tile/map aperture를 읽어 consume·receipt·최종 ACK까지 진행한다. 전체8570B map/CGRAM/OAM/HDMA metadata 및 모든 tile 바이트를 기존 C 결과와 비교한다. warm 초기값은 같은 bank의 두 프레임 전 기록이다.

manifest10/11은 전송/ACK와 원래 payload 보존을 확인한다. 이 시험 모델이 manifest 의미와 모든 SEAL 조건을 다시 구현한 것은 아니다. H2는 ARM에서 의미·digest·certificate CRC까지 만들어 기존255 인증서와71개 모두 비교한다. epoch는 이 진단의1로 고정되어 있으며 제품의 runtime admission 문맥 연결은 남아 있다. CRC는 오류 검출이며 인증이나 충돌 부재 증명이 아니다. 출력 모델의 H2 수신 검사는 형식뿐이며 실제257 core의 H2/receipt 의미 검사와 이번 전체 명령열은 아직 연결되지 않았다. receipt 응답은8NES-cycle endpoint다. final ACK는 논리적 퇴역 확인이며 최종 VBlank 표시 시각이 아니다. 이전258의 실제65816/VRAM 한 범위 검증은 보존하지만 이번 전체 명령 시험을 실제65816 실행으로 부르지 않는다.

ARM 71개 연속 계획에서4credit 사용, token 진행, 일반 명령/범위/H2 일치를 확인했다. accepted/retired는16비트 순환 차이로 credit를 계산한다. 검토 중 제거한65,535 전송 중단 조건은 제품 장시간 실행에 불필요한 제한이었다. 빈 queue의 두 counter를65,530에 맞춘 독립 시험으로 순환을 확인하며 이는 일반 실행의 측정값과 분리한다. ARM 음성12개는 status CRC, accepted/retired 불일치, tile generation/길이, tile-end 누락, F7 거부, token 고갈, 잘린 계획, map tag, HDMA 의미, serial 오류를 검사한다. RTL은 공유·분리 각각 정상+16검사로 bank/token 재사용과 중간 취소를 재확인했다. 실패와 중간 성공은 모두 보존한다.

## 공유 SPI와 tile 경쟁

`probe_nes_bus259.py`는 source257 transport와 output259를 같은 SS/SCK/MOSI/MISO에 연결한다. 실제 ARM D0/D1/D2/D3 코드가 입력을 읽고 CRC/독립 digest를 확인한 뒤 출력 명령을 전송한다. source와 output이 동시에 MISO를 소유하면 실패한다. 입력 ACK 뒤 표시 identity를 열며 입력·출력이 같은 버스를 동시에 쓸 수 있다는 가정을 하지 않는다.

이 입력은 기존255 N5 payload를 진단용243B record로 잘라 공급한다. 실제 query/encoder의 생산 지연, N5 의미 복원·화면 계획, 공용 core CRC datapath는 포함하지 않는다. source transport에 CRC 응답을 주는 시험 회로는 별도이며 이 회로를 아래 출력 MAP에 포함했다고 계산하지 않는다. 입력 FNV는 fixture 일치 oracle로서 제품 검증기나 인증이 아니다.

tile206 생산자는 실제 연결하지만 upstream tile192/ROM arbiter는 아직 붙이지 않았다. 바이트 공급 대기를4NES-cycle에서64cycle로 늘리는 민감도 시험으로 경쟁의 영향을 확인했다. 954에서 출력10.95703→11.49284ms, 상태 조회34→40회, SPI2868→3012B가 됐다. 수정 전 slow01은 “미준비”를 오류로 처리해 실패했고 수정 후 slow02는 통과했다. 고정 FETCH_WAIT를 실제 ROM 최악 지연 측정으로 해석하지 않는다. 현재 일정은 모든 tile 종료 뒤 map을 시작하므로 map/tile 동시 생산 능력을 검증한 것이 아니다.

## 시간 비용과 판정

시험의 host clock은100MHz, NES clock은약22MHz, SPI는2.625MHz다. ARM 명령 사이에 `명령수 × CPI /84MHz` 시간을 흘린다. CPI1 기본과 CPI2 민감도는 가정이며 Cortex-M4 cycle 측정이 아니다. SNES 서비스는 버스200ns active+200ns release, DMA setup500master-clock에 해당하는23.28us, COPY/fill 바이트560ns를 배정한다. RPC의10us 초기 준비와 전송당10ns+1000ns도 ARM 완료 일정에 포함한다. 마지막 DONE의100us 시험 정착 대기는 유효 작업에서 제외한다. 메타데이터 최종 PPU 업로드, VBlank, 실제 드라이버/IRQ/cache/wait-state 비용은 열려 있다.

| frame | 기존 입력 RTL ms | ARM 출력 완료 모델 ms | 직렬 합계 ms |
|---|---:|---:|---:|
| 952 | 4.528955 | 10.118334 | 14.647289 |
| 954 | 6.255045 | 11.047110 | 17.302155 |
| 955 | 4.279045 | 11.564991 | 15.844036 |
| 962 | 5.095045 | 11.480263 | 16.575308 |
| 963 | 5.066091 | 12.033842 | 17.099933 |
| 968 | 4.726682 | 9.513140 | 14.239821 |
| 970 | 6.276409 | 11.762866 | 18.039275 |

7개 중954/963/970이16.667ms를 넘고962도 나머지 비용 여유가 약0.091ms뿐이다. 이 표는 cold나 최종 표시까지 포함한 실제 프레임 측정이 아니다.

954 기본 출력은184935 ARM명령,2868SPI bytes,60packets,48DMA chunks,714DMA bytes이며 최종 RTL ACK는10.95703ms다. 마지막 상태 수신 뒤 CRC 검사/함수 반환까지 포함한 ARM 완료 일정은11.047110ms다. 이전255의 같은 프레임 입력6.255045ms를 직렬 결합하면 **17.302155ms**다. 서로 다른 시험을 묶은 조건부 값이며 물리 측정이나 일반적인 불가능성 증명이 아니다. 기존 전체 display sample을 여기에 그대로 더하면 이미 처리한 map DMA를 중복 계산할 수 있으므로 더하지 않는다. 최종 표시의 나머지 비용을 별도로 결합해야 한다.

같은 핀에 입력 transport도 연결한954 진단은1758B 입력,106136 입력 ARM명령,전체4794SPI bytes/291080ARM명령으로 RTL 최종 ACK18.11667ms, ARM 완료 일정 **18.206709ms**였다. 이 값에는 입력 SPI가 이미 포함되므로 이전 입력6.255045ms를 다시 더하지 않는다. 실제 planner/query 지연을 무료로 둔 이 특정 진단 일정도16.667ms 안에 들어오지 않는다. 이를 full RUN의 측정된 하한이나 모든 전송 방식의 실패로 확대하지 않는다. 963의 같은 핀 진단도 입력1411B/전체4670SPI bytes, RTL ACK17.67099ms/ARM 완료17.761168ms로 통과했다. heavy7와 cold 및 CPI 민감도의 개별 결과는 비용 CSV에 고정한다.

954의 map 값은154B지만45개 범위마다 패킷을 만들면서 제어1035B를 더해1189B를 보낸다. 전체 F8 조회는816B다. source+output 같은 버스에서 이 패킷/조회/CRC 비용을 숨길 수 없다. 단순 ARM 검사 위치 이동이나 회로 축소만으로 해결했다고 볼 수 없다.

## 같은 출력 경계의 회로 비용

| Quartus Lite MAP | 분리 staging | 공유 staging | 공유−분리 |
|---|---:|---:|---:|
| LE | 3467 | 3282 | −185 |
| comb | 2133 | 2072 | −61 |
| FF | 1838 | 1667 | −171 |
| RAM bits | 73984 | 41216 | −32768 |

두 구성은 같은 직렬 ownership 일정이며 staging만 다르다. 이전258 공유3319LE/2062comb/1751FF에 비해259는37LE·84FF 줄고 comb10개 늘었다. status 확장과 completed-ACK 제거를 함께 적용한 결과다. 원인을 개별 gate 절약으로 임의 분해하지 않는다. 테스트/MAP의9개 RTL hash를 대조하며 새 ARM phase wait는 RTL을 바꾸지 않았다.

이 top은 출력 queue/ACK/parser/tile206/aperture/CDC/token/receipt/final ACK까지다. source/core/collector/display lease/upstream tile192/ROM arbiter는 밖이다. 두 모듈의 MAP을 더하거나240의490LE/40LAB 부족에서185LE를 단순 차감하지 않는다. whole FIT/STA/CDC/IO와 mapper 여유는 아직 없다. 출력 ARM 코드는2120text/0data/308bss, 관측 stack120B이며 source 진단을 함께 링크하면2528text/관측 stack328B다. caller의8570B metadata와 입력 계획, RUN/IRQ stack 및 기존 버퍼의 교체 여부는 별도로 산정해야 한다.

사용자 결정에 따라 **앞으로 Quartus Lite를 기본으로 사용**한다. 이번 두 MAP도 Lite25.1std.0 Build1129에서 성공했다. Standard 평가판을 재시도하지 않았고 구매/전역 설정 변경도 없다. Questa는 설치 경로에 `altera_standard`가 있어도 기존 무료 Starter FLOAT workflow로 실행하며 Quartus Standard 구매와 별개다.

## 다음 후보와 검증 순서

다음은 여러 map 범위를 한 패킷의 head 아래 유지하고 범위별 DMA·receipt 이후에만 전체 packet을 retire하는 구조다. token base/count를 packet에 묶고 tile barrier 뒤 연속 예약하는 후보를 우선 비교한다. 예시 포맷16B header+4B base token+1B count, 범위당3B descriptor, 값,3B SPI/CRC를 단순 포장하면954의45범위를2packets/337B로 줄일 수 있다. 기존1189B 대비852B, wire-only 약2.597ms 절약이다. **아직 새 parser/credit/취소 RTL이나 처리 시간으로 검증한 결과는 아니다.** 상태 조회 감소나 CRC/ARM 절약을 추가로 공짜 계산하지 않는다. 954의 원래 최대 범위는8B여서64B 상한만 늘리는 것으로는 이45개 범위의 패킷 수가 줄지 않는다.

같은954에 gap16 병합을 함께 적용하는 포장 후보는32범위/244값 bytes/2packets/388wire bytes다. 정확 범위 batch337B보다51B, SPI 약0.155ms가 더 들고 DMA도90B 늘어난다. 반면 setup500 배정에서는13회 setup, 약0.303ms를 줄일 수 있다. 시험 bus의 추가90B 약0.037ms까지 단순 직렬 배정하면 차이는 약0.110ms다. 이 계산은 새 RTL/ARM/SNES 실행 결과가 아니며 batching 자체의 큰 전송 절약과 분리한다. gap만 작은 값으로 바꾸는 반복 최적화를 주된 답으로 삼지 않는다.

이 후보는 packet head를 오래 보유하므로 공유 RAM 포트, consume/receipt/backpressure, 부분 취소, token 끝값을 함께 설계해야 한다. source+output 동일 SPI, 실제 tile192/ROM arbiter, full ARM N5/planner/RUN/IRQ, 실제 SNES 명령/setup/최종 표시와 묶어 동일 프레임 비용을 다시 판정한다. 최악 잔여 시간과 전체 회로 교체 경계가 타당할 때만 whole FIT/STA로 진행한다. 개별 CRC/ROM/opcode/seed 조정이나 반복 FIT는 다음 목표가 아니다. production227/GBC164/saveSRAM은 유지한다.

## 재현

`probe_nes_arm259.py`와 `guard_nes_arm259.py`는 Unicorn2.1.4/pyelftools0.33 및 ARM GNU13.3.rel1 toolchain을 사용한다. 패키지는 프로젝트 `.tools/arm259-python`에만 설치했다. `probe_nes_output259.py`, `probe_nes_bus259.py`, `gate_nes_output259.py` (MAP 옵션 없이)는 승인된 `probe_float.ps1 -RunOnly -AfterSmokeScript <absolute job> -QuestaBin <bin>` 안에서 실행한다. Quartus MAP은 `gate_nes_output259.py --map-test <passed RTL run> --shared 0|1`이며 Lite만 사용한다. 모든 출력은 새 경로로 만든다. 공개 분석기는 계획의 선택 경로를 재검사한다. ROM·map·tile payload와 raw log는 비공개 `probes/nes-output259`에 보존한다.

초기 실패도 선택 증거와 분리해 보존한다. arm01은 sandbox DLL 실행 오류, rtl01은 선언 순서 compile 오류, rtl02는 느린 Tcl bit 구동 중단, rtl03은 force 숫자의 radix 해석, rtl04는 Windows 파일 공개 순간의 공유 잠금, guards01은 testbench의 잔여op9 변환 누락이었다. slow01은 실제 미준비 tile 처리 결함이었다. 내부 SPI 구동기/명시적10진 force/제한된 파일 읽기 재시도/phase wait로 각각 수정하고 새 경로에서 통과한 결과만 선택했다. 중간 arm02..04 및 이전 성공 실행을 최종 코드의 증거로 섞지 않는다.

집계 analysis01은 ELF 파일 전체 해시가 같다는 과도한 조건에서 중단됐다. GCC가 assembler 임시 object 이름을 `.strtab`의 STT_FILE에 남겨 파일 해시는 달랐지만 로드할 코드/메모리와 나머지 symbol은 같았다. analysis02는 각각의 원본 ELF 해시를 보존하면서 모든 PT_LOAD bytes/address/size 및 non-file symbol을 비교한다. 실제 코드 차이를 허용한 것이 아니다.

최종 선택은 arm05/arm-guards03/guards02, 출력 wrap01/rtl07/cold03/heavy03/slow03/cpi04/heavy952/955/962/968/970, 같은 핀 bus02/bus963, MAP separate01/shared01, analysis02다. 선택 증거719개 hash와13개 연결 실행을 검증했다.

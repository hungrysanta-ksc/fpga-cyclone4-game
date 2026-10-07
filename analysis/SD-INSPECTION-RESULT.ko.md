# NES SD 원본 수집 준비 결과 — 072

## 작업 목표

실기가 PC 밖에 있다는 조건에 맞춰 원본 firmware/base/menu의 정보를 **수집 펌웨어→사용자 SD 실행→TXT 반환**으로 확보할 준비를 한다. PR26 병합 `dbb4a3b171651363ed913ffeb3c0e5ab3265eb66`에서 진행했다. CF68 설치 전에 원본과 수집기 자체를 구분하고, 실제 메뉴 분류에 필요한 헤더/reset 정보를 남기는 범위다.

## 작업 내용

SDINFO072-BASE069 전용 MCU를 만들었다. 입력은 원본 firmware 사본·현재 firmware·기본 FPGA·메뉴4개다. 전체 CRC/STM3 본문/RLE 복원 CRC·길이와 메뉴 후보 헤더6개/reset byte를 고정 상한으로 읽는다. 기존 보고서와 입력을 덮어쓰지 않고 루트 HW003000–HW003999에 새 TXT를 쓰며, sync/close/재읽기/크기·모든 바이트를 대조한다.

수집부터 마지막 화면까지 RESET/USB와 SD offload 보호를 유지한다. native 공유 오류/예산 초과 뒤 추가SD·base·close를 금지한다. 정상/논리 파일 오류는 상태 화면에서 멈추고 게임 메뉴는 실행하지 않는다. 이전 mini 초기화와 file_init은 수집 예산 이전의 legacy bring-up이다. 전체 부팅의 종료시간이나 실물 동작까지 확인했다고 쓰지 않는다.

호스트 수집52·저장23·실제 platform C6세션·TXT검사29가 통과했다. readback 비교 제거와 조기 diag_leave 대조2개는 인과 assertion에서 실패했다. ARM13.3.rel1/Make3.81 전체 링크의 main→sdinv_run 및 수집/쓰기/마지막 오류 확인/leave/RESET 해제 순서를 확인했다. ELF에 기존 메뉴/FPGA/START 함수가 남지만 전용 main의 실행 경로는 구분한다.

새 ARM 전달본132768바이트 SHA `8215d81dd84a07f3dfffe5163163c07ef1166fcbfab25b95cbc4942dbc42f724`를 펌웨어 하나만 포함한 수집 zip과 대응 소스 zip으로 준비했다.069 archive의275개 실제 입력을 대조하고 archive 밖의 config/VERSION 등도 새072 입력1333개로 고정했다. 공개 준비 도구와 최종 main/Make/VERSION/newC7입력은 바이트 동일하다. HWINFO002 mini 입력은 동일 해시다. 새 RTL/fit/STA/ASM/Questa/CF68 펌웨어 교체는 없다.

동결 `probes/nes-sd-inspection-072/evidence/` **1411파일**, manifest `c10bb9f31911addb4dd87f9258bc84a3074dca7574db3a2b1003aeca921f3c39`. read-only audit 통과, 기존071374파일도 다시 통과했다. Git에는 코드·문서·요약만 공개하며 바이너리/원시로그/실물 파일은 없다. 대응 소스는 별도 전달한다.

최초275입력 개수 기대·VERSION separator/잘못된 CONFIG_VERSION로 인한 SNAPSHOT·TXT repaired framing 기대 오류와 raw 로그/전사를 보존했다. 최종 소스 대조에서는 VERSION의 CRLF/LF 차이가 먼저 실패했다. 실행 원본을 바꾸지 않고 공개 준비 도구가 CRLF를 재현하도록 수정한 뒤 새 clone의7입력을 모두 대조했다. 이 마지막 실패는 동결 밖 `reproduction-review.ko.txt`에 terminal 전사로 남기며 동결 파일을 사후 편집하지 않는다.04 링크/최종 시험·고정 전달본만 성공 근거다.

## 작업 결과

**수집기 구현·호스트/ARM 검증·외부 전달본 준비라는 목표는 달성했다. 실제 SD 정보를 확보하는 목표는 사용자 실행과 TXT 반환까지 미달성이다.** [실행 안내](../docs/SDINFO072-RUN.ko.md)에 교체 전 독립 전체 백업·원본 firmware 사본·실행·TXT 전달·원본 복원과 GBC 관측을 정리했다.

실물 SD/STM32, 실제 메뉴 분류, 독립 백업/readback/복원, 전압/PCB/비동기SPI/SNES와 lockedHIGH CE>8µs 한계는 남는다. CRC는 인증/SHA/실물 실행 증명이 아니다. `TXT SAVED`도 입력 승인/메뉴/GBC 정상이라는 뜻이 아니다. 준비도 **5완료/6부분/1미완료**는 작업량 비율이 아니며071 NES 쌍은 installable=false다.

다음 목표는 새 HW003nnn.TXT와 원본 복원 관측을 받아 입력 상태를 확인하고, 실제 menu smc_id/sgb_id·mapper/carttype/offset/payload 분류를 bounded 입력으로 대조하는 것이다. 부품/분해/PC USB를 다시 요청하지 않는다. 기존044 화면 순환/GBC 성공과 GBC152/originalNES334 보호 해시를 유지한다. [계약](../docs/nes-sd-inspection-contract.md)·[인계](../cores/nes/HANDOFF.ko.md).

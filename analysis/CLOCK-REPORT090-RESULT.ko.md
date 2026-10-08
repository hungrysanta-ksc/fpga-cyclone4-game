# NES090 클록 관측과 TXT 전체 세션

## 작업 목표

PR40 병합과 master `6077d65b26ac53b6fc5f029aa1e7fb332d519b9d`의 이전 head 도달을 확인했다. 기존 분리된 구성·관측·저장 경로를 하나의 제품 함수로 연결하고 전체 예산과 최종 ARM 링크를 검증한다.

## 작업 내용

090는 단일 제품 함수의 CF87 구성·클록 관측·mini 복귀·실제 SD 초기화/FatFS·TXT 저장/재읽기·최종 화면을 연결했다. 통합94검사·인과 대조4개, TXT16파일 대조와4변조 거부, 전체 ARM196248바이트 링크/호출 검증을 통과했다. 실제 SPI 핀 전환 점검과044 복원 포함 패키지 검증은 남아 있어 실기 배포 전이다.

사람이 읽는 네 결과와 원시 snapshot을 `/HW090nnn.TXT`에 기록한다. ACTIVE는 주파수 승인과 구분한다. 기존084 저장/정상044복원/menu/GBC 실기 PASS 및 네이티브13입력, 기존087fit/088reader/089config는 보존했다.

## 작업 결과

**이번 범위인 제품 통합·전체 호스트 세션·ARM 링크 목표는 달성했다. 실기 진단 배포 목표는 아직 미완료다.** 정상 FAT16/32의 writer 전 공유 검사739341/739342회, NO_PROGRESS931395/931396회, dense FAT32 최장955390회로 기존100만 한도를 넘지 않았다. writer는 기존 별도10초/10000회 범위에서60회다. 모든 SD나 실제 시간에 대한 보장은 아니다.

firmware196248바이트 SHA `00f757fcd1ca0da08ce0e5564358e06b482071e6119d8827e6c81748fcfddebe`, 고정CF87 RLE59700바이트 SHA `e772ead5e070c71767df2318d91f5d83d629e8ffedd275b19e81c842133cb4a2`. main→단일 플랫폼→구성/관측→mini→SD/저장 호출 순서를 disassembly에서 확인했다.11소스 전체 및 menu runtime prefix가 host와 같다. ARM 실행/실기/새RTL/Questa/fit/ASM은 하지 않았다.

Make 최초 dependency 실패와 retry 로그를 보존했다. 첫 ARM checker의 전체 menu C 비교는 host가 제외한 미사용 메뉴복사 함수 때문에 실패했으며, 정확한 prefix 비교로 수정했다. 코드/펌웨어는 변경하지 않았다. host01은93, 최종host02는94이며 TXT parser의 initial 미획득 경계는 text01에서 별도 검증했다.

다음 완료 조건은 실제 GPIO/SPI/RESET 구성 전환의 연속성 점검과 동일 firmware·CF87·mini·정상044 복원 파일을 묶은 report-only trial/source 패키지 검증이다. 이후 사용자 TXT/화면으로 기준 클록 가용성을 판단한다. CF86 외부PSRAM/async/common-cause 및 전체 NES 세션은 별도 미완료다.

[계약과 재현·미완료 항목](../docs/nes-clock-report090-contract.ko.md), [검증 메타데이터](clock-report090-verification.json). 동결2063파일 manifest `5ecbc6fe3f5580943d0a9d991d880595caa1d30db37cb78815114bc2c42f0512`. 준비도4완료/7부분/1미완료, installable=false. 완료 finalizer 재실행/044–089 archive 수정 금지.

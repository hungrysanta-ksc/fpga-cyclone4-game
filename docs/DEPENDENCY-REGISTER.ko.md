# 소스·라이선스·의존성 등록부

현재 저장소에는 원본 RTL·MCU/renderer 구현을 아직 등록하지 않았다. 아래 commit은 로컬 조사 기준이며 코드의 공개 허가 판정이 아니다.

| 구성 | 로컬 조사 기준 | 등록 상태 | 다음 검토 |
| --- | --- | --- | --- |
| Gameboy_MiSTer 기반 GBC core | 로컬 upstream HEAD `7a5ff50528cd9c1d13ffb675e7df8506bffaa078`, 수정된 파일 있음 | 미등록 | 공식 upstream URL/라이선스/각 수정 파일의 출처와 필수 HDL·boot image 의존성 확인 |
| sd2snes/FXPAK MCU·FPGA·SNES 경로 | 로컬 upstream HEAD `cf7e21d7a5978fcd74981d71c3cfbf6e982a4dd1`, 수정된 파일 있음 | 미등록 | 각 하위 파일의 저작권·라이선스, 변경 diff, board definition·build 도구 의존성 확인 |
| 공개 저장소 자체 문서·감사 도구 | `codex/methodology-baseline`의 초기 문서/도구와 후속 관리 문서 | 등록 대상 | 전체 공개 재사용 라이선스는 소유자 결정 대기 |
| 상용 게임 ROM/SaveRAM/boot image·사용자 dump | 개인 로컬 시험 자료 | 영구 제외 | 빌드/시험 방법에는 파일 해시·형식만 기술, 내용·식별 정보 공개 금지 |

향후 코드를 추가할 때 한 행에 upstream URL, 고정 commit, 원래 라이선스/NOTICE, 수정 파일 목록, 생성물/헤더 포함 경로, 필요한 도구/버전, 공개 가능한 무ROM 테스트, 검토자를 채운다. 저장소 루트에 단일 LICENSE를 서둘러 추가해 서로 다른 upstream 조건을 덮지 않는다.

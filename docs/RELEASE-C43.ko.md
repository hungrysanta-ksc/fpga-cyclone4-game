> Historical C43 preparation record. Current: [C44 release](RELEASE-C44.ko.md), [user guide](USER-GUIDE.ko.md), [build](BUILD-C44.ko.md).

# C43 배포 준비

현재 상태는 **C43 소스 정리·재현 검증 완료 / C44 로그 OFF 실기 시험 대기**입니다. 사용자 요청으로 GitHub 푸시·PR·최종 Release를 모두 보류했습니다. C44 통과 후 최종 소스와 업데이트 ZIP을 확정합니다.

## 완료 범위

- 사용자 실기 성공 기록과 지원 매퍼·기능의 경계 정리.
- FPGA 소스·제약, MCU 변경 파일 29개, renderer 생성기, 고정 upstream 커밋 등록.
- 원본 성공 C43 실행 파일의 SHA256 고정.
- SGB 코어·SGB BIOS·게임 ROM·세이브를 제외하는 4파일 업데이트 패키징.
- 공개 가능한 RTC 레지스터·SPI 회귀검사.
- 최종 재현 빌드 결과는 `release/rebuild-verification.json` 참조.

C43 기존 fit: 15,155/15,408 LE, M9K 56개 사용, setup 최솟값 +0.056ns / hold +0.072ns. 제약을 완화하지 않았습니다. 자원 여유가 작으므로 정리 목적의 RTL 변경도 새 후보로 다시 검증해야 합니다.

## 최종 발행 전 남은 항목

1. 자체 작성 소스의 재사용 라이선스 범위와 upstream 개별 헤더 없는 파일의 고지를 확정합니다. GPL/MIT/Intel 조건을 하나로 덮지 않습니다.
2. 기존 타이밍 문서의 미제약 경로·CDC·보드 검증 경계를 유지합니다. 성공 실기 표본과 양수 constrained slack을 전체 보드 signoff로 표기하지 않습니다.
3. 공개 업데이트 ZIP의 설치 절차를 기존 1.11.2 SD 복사본에서 한 번 확인합니다. 성공 바이너리는 같으므로 전체 게임 목록을 다시 반복할 필요는 없습니다. SGB 파일 없이 `.egbc` 부팅, 기존 SGB 설치를 유지한 `.gb` 선택을 간단히 확인하면 됩니다.
4. PR 검토 후 버전 태그·릴리스 설명·SHA256SUMS와 소스 묶음을 같은 후보로 게시합니다.

이번 단계에서 기본 브랜치 병합·최종 릴리스 발행·기존 실기 성공본 교체는 수행하지 않습니다. 소스 업로드와 패키지 준비를 완료한 뒤 위 남은 항목을 별도 판단합니다.

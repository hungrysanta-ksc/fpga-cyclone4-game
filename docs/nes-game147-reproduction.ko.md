# NES147 실제 ROM 실행 재현

로컬146 증거와 사용자가 보유한 정확한 SMB3(J) ROM이 필요하다. ROM SHA256은 `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`다. 공개 저장소에 ROM을 복사하지 않는다.

기존 `probe_float.ps1 -RunOnly -AfterSmokeScript <절대 작업 스크립트> -QuestaBin <설치 경로>`를 사용한다. 한 번에 한 FLOAT 작업만 실행하고 원래 라이선스 및 전역 환경을 변경하지 않는다. 아래 명령은 해당 wrapper의 자식 작업에서 실행하며 Python·도구·입력은 절대 경로, 출력은 새 ASCII 디렉터리로 지정한다.

```text
python -B tools/nes_game147.py --baseline <probes> --rom <사용자-ROM> --out <새-core-출력> --questa-bin <Questa-win64> --frames 30 --prefetch
```

현재 결과는 26번째 프레임 PPU deadline 실패이며 종료 코드가 0이 아니어야 한다. `--prefetch`를 생략하면 기본 경로는 24번째 프레임에서 실패한다. 프로그램은 실패를 PASS로 바꾸지 않으며 원본 `simulation.log`와 `result.json`을 남긴다. 입력 소스는146 manifest·개별 해시를 확인한 뒤 새 출력 디렉터리에 생성한다.

생성된 core 디렉터리를 사용한 별도 FLOAT 작업:

```text
python -B tools/test_nes_game147_path.py --prepared <core-출력> --out <새-unit-출력> --questa-bin <Questa-win64>
python -B tools/test_nes_game147_prefetch.py --prepared <prefetch-core-출력> --out <새-boundary-출력> --questa-bin <Questa-win64>
```

첫 시험은 실제 경계 쓰기·읽기와19비트 상태를 검사하지만 전체 적재는 생략한다. 두 번째는 기록된 첫 실패의 캐시 상태를 주입하는 짧은 재현이며 전체 PPU 동작을 보증하지 않는다. 두 시험 통과만으로 core03의 실패나 실기 미완료 상태를 해제하지 않는다.

원본 로그·ROM 데이터·프레임은 로컬 증거에만 보관한다. 공개 메타데이터의 `manifest_sha256`은147 보존 증거를 가리키며146 증거를 덮어쓰지 않는다. 같은 입력의 긴 실행을 이유 없이 반복하지 않고, 다음 수정의 첫 실패 경계와 실제 게임 실행을 확인한다.

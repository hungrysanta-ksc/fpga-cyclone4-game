# NES105 파일 조합 재현 계약

104 동결 evidence와091 보존 trial ZIP을 읽기 전용 입력으로 사용한다. 기존 출력/SD/증거를 덮어쓰지 않고 새 경로만 만든다.

```text
python -B tools/prepare_nes_pair105.py --evidence104 <104-evidence> --restore091 <091-trial.zip> --out <new-review>
python -B tools/nes_pair105.py --review <new-review> --manifest-sha256 <independently-recorded-digest>
python -B tools/test_nes_pair105.py --review <new-review> --out <new-tests>
python -B tools/verify_nes_pair105.py --evidence <105-evidence>
```

검토기 통과는 파일 정체성과 역할의 일치만 뜻한다. installable/hardware_trial_approved/start_enabled/external_io_signoff/both_clock_halt_safe/persisted_report_proves_reset_release는 모두false다. manifest를 편집하고 digest를 갱신해도 승인으로 바꿀 수 없다. 실제 전달 승인이나 SD 설치 기능은 없다.

CF86 압축은071 공개 decoder로 전체 대조한다. 받은base는097 실제C 해제 근거와 정확 해시를 재사용하고 legacy 패딩을 변경하지 않는다. 합성fixture80/96과 SMB3 상용ROM을 혼동하지 않는다. 복원044와진단104는 동일SD대상명이나 별도역할이다.

094 선택/로그 이름은 의도적으로 유지된 제품 계약이다. TXT의 PREPARED_RESET_HELD는 RESET 해제·메뉴 화면 증명이 아니다. 새로운 실기 절차에는 이전TXT 분리, 새파일·화면 관측, 오류시 전원종료/수동044복원과 관측한도를 포함해야 한다. 현재 문서는 설치 실행 지시가 아니다.

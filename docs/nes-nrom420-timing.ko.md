# NES420: Lite 후보와 224의 timing·CDC 경계 비교

419의 FIT DB에 기존 224와 동일한 Lite Timing Analyzer 경로 추출·CDC inventory·reset207·조건부 IO 계산을 실행했다. **raw 전체 STA는 여전히 setup −6.970ns, recovery −8.824ns이며 미제약 경로와 무시된 max-delay가 있다.** 224 방법과 비교하기 위한 분류 결과를 raw 전체 STA 통과로 바꾸지 않는다.

기존 224의 관련 clock 경로 분류에서는 세 코너 nominal/implementation 최악 setup +0.176ns, hold +0.164ns다. source epoch 96개 레지스터의 recovery/removal 576개 경로 최솟값은 +1.737ns, 동기화 첫 단계 45개의 fanout 검사는 일치했다. 기존 분류에서 새로운 direct-path 미분류 0개, held payload 최대 6.442ns, gray 첫 단계 최대 6.692ns다. 다만 `inherited_unmodified` 1,716행과 `inherited_reset_review` 1,272행은 분류일 뿐 전체 독립 재검증 결과가 아니다.

224의 가정된 조건부 디지털 IO 계산은 PSRAM margin +2.775ns, SNES read envelope 84.518ns(모델 한도 270ns), SPI reply 167.196ns(2.625MHz 반주기 190.476ns), native payload 음의 reset 경로 0개다. 이 계산에는 기존 70ns PSRAM 및 보드 allowance 등 가정이 있고 전기적 IO·MTBF 완전 승인이나 대표 실제 observer 전체 시나리오가 아니다. 전체 음의 reset 경로 39개는 여전히 남는다.

결론은 이전의 `−6.970ns` raw 경고 중 최악이 서로 다른 도메인의 reset 관련 경로라는 점과, 224의 제한 분류에서는 관련 clock 경로가 양수라는 점이다. 실기 진입 전 inherited reset 39개 및 미제약 포트·무시된 loader state 제약을 실제 경로별로 감사하고, 조건부 IO 가정·FPGA/firmware/65816 패키지 및 복구를 확인해야 한다. 임의 false path나 전체 STA 성공 주장 없이 그대로 보류한다. 원본 및 경로 TSV는 `probes/nes-nrom419/fit01`, 재현 계산은 `analysis/nrom420-timing.json`이다.

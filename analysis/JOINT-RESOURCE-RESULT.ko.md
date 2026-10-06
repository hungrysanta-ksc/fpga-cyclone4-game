# 코어와 전송부 공동 배치032
2026-10-06. 후보 NES-R1-JOINT-RESOURCE-032. Core014/RTL interface031/H0실기030 유지.

**기존 코어+기본 RAM과 새 전송부를 같은 FPGA에 넣는 배치가 성공했다.**
별도 결과의 LAB 합992가 기기963을 넘었던 의문을 실제 공동 배치로 확인했다.
코어·매퍼·RAM·전송부의 소스 바이트를 바꾸지 않았으며 추가seed나 완화설정은 사용하지 않았다.

|항목|018+031 별도 수치 합|032 공동 배치|기기 용량|산술상 남음|
|---|---:|---:|---:|---:|
|LE|13,420|13,417|15,408|1,991|
|LAB|992|923|963|40|
|M9K|24|24|56|32|
|payload RAM bits|172,032|172,032|516,096|—|

LAB는69개 적게 배치됐고 LE차이는3개다. 논리 기능을 줄인 결과가 아니라 같은 소스를 함께 배치한 결과다.
내부 목표13,000LE보다417개 많으며,전체 LAB의 약95.85%를 사용한다.
40LAB는 실제 후속 기능을 배치·배선할 수 있다는 보장이나 예약된 여유가 아니다.

## 실제 실행과 보존 확인
Quartus25.1std build1129, EP4CE15F17C8, seed1. map/fit 모두 exit0.
CPU/PPU/APU/MMC3 및 SNES frontend hierarchy가 남았고,
CPU RAM2KiB/CIRAM2KiB/PRG RAM8KiB/packet queue6KiB/stage3KiB가 모두 유지됐다.
RAM별 M9K는2/2/8/8/4다. 전체21KiB payload와24M9K를 보고서에서 재검증했다.
CPU1145/APU1386/PPU9345cells 중 OAMEval7903cells가 포함된다. 부모·자식 값을 이중 합산하지 않는다.
새 최적화나 기능 변경 없이 첫 map/fit 실행에서 성공했다.

## 이 결과의 경계
이번 top은 **공동 배치를 위한 자원 probe**다. NES master와queue clock을 공유하지만
실제 NES영상→packet encoder/producer는 연결하지 않았고,producer입력은virtual pin으로 남아 있다.
018의기본RAM어댑터도기능검증완료품으로격상하지않는다.
281virtualpins와위치미할당clock2pins를사용했다. 물리board PLL/핀/IO/CDC·외부메모리·MCU/renderer loader·음향출력이없다.
클록46.560846/11.904762ns는모델선언이다. STA를실행하지않았으며fit보고서의Timing Models:Final은STA완료표시가아니다.
이 probe로실기용bitstream이나새게임패키지를만들지않았다. CPU/APU정확도나게임호환성결과도추가하지않았다.

map경고10335/10027/10230/13046/13049/276020/276027/12241/13024/13410,
fit경고169085/114001/169177을보존했다. 내부tristate변환·배열index/폭·RAMpass-through·clockpin미할당·주기절삭등이포함된다.
경고를0으로표시하거나false path/주기완화로숨기지않았다.

## 이후 순서
1. H1 자체 패턴 생산기와실제SNES PPU DMA클라이언트를031 MMIO경로에연결한다.030에서확인한큰제목/페이지/오류표시방식을유지한다.
2. H1 보드PLL/reset/핀/IO/CDC와loader/복귀를구현하고동일후보의전체fit/STA를검사해실기묶음을준비한다.
3. 실제NES encoder/외부메모리/renderer/clock전략의비용을하나씩추가해40LAB 여유를재측정한다.
   자원초과가실측되면메모리/중복제어구조부터검토하고,OAMEval동작수정은별도동등성·기능회귀후에만채택한다.
현재공동배치가성공했으므로이번단계에서OAM기능을단순화하거나화면crop/프레임누락/감속을도입하지않는다.

H0는사용자5.27초영상의기본육안순환통과상태다. H1 실기·전체NES실기는아직미완료.
[검증 수치](joint-resource-verification.json), [재현 계약](../docs/nes-joint-resource-contract.md).
원시: analysis/local-joint-resource-032/run.이전031manifest157항목을검증하고현재상태8개를baseline-status에보존했다.
GBC C44/0.9.0,core014,031RTL,upstream불변.이번에는Questa/Mesen/라이선스서버를실행하지않았다.

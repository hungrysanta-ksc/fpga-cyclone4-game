# 저장소 작업 지침

## 먼저 읽을 문서

1. `README.md`: 프로젝트 목표·코어별 현재 상태.
2. `docs/PROJECT-STATUS.ko.md`: 현재 실기 기준과 미완료 항목.
3. `docs/development/RESUME.ko.md`: 새 PC·새 작업의 재개 절차.
4. 해당 코어의 README와 HANDOFF, 관련 `docs/progress/pr-NNN.md`만 추가로 읽는다.

과거 누적 README/AGENTS/HANDOFF는 `docs/progress/archive/`에 보존했다. 그 안의 Current/FIRST/NEXT·예전 승인 상태를 현재 지시로 실행하지 않는다. 실험 번호와 PR 번호를 혼동하지 않는다.

## 현재 작업 범위

- [598 collector·출력 비용](docs/nes-boundary598-results.ko.md). 598의 collector 요약은 53입력·1,537그룹에서 일치하고 905/906의 D0를 11/10회 줄였다. 결합 MAP은 4,910 LE로 새 경계 상한보다 907 LE 크다. [599 출력 실측](docs/nes-output599-results.ko.md)에서 상속 CRC만으로 두 위상의 기준 최종 ACK보다 12.077–15.995 ms 늦었다. [600 실제 SPI·ROM 비용](docs/nes-wire600-results.ko.md)에서 562/558 B를 줄였지만 필수 조회를 포함한 wire 하한은 16.808/17.030 ms였다. 601에서 현재 PPU 캡처를 재사용해 952·954의 208/272개 요청을 모두 충족했다. 두 위상의 낙관 표시 간격은 31.443–31.900 ms다. [601 검증](docs/nes-snoop601-results.ko.md) 602의 4 B D2는 두 장면에서 60 B를 절감했다. 한 슬롯의 D1 중첩은 0이고 두 슬롯을 가정해도 표시 전 5.144–5.587 ms가 더 필요하다. [602 검증](docs/nes-overlap602-results.ko.md) 603의 compact palette는 290 B를 줄이지만 65816 복원·검사가 12.014 ms로 기존 palette ACK보다 8.585–8.708 ms 늦다. [603 검증](docs/nes-palette603-results.ko.md) 604에서 실제 행 압축·ARM 복원으로 278 B와 첫 BG 1.668 ms를 줄였으나 두 위상의 첫 ROM 허용 시각은 같았다. [604 측정](docs/nes-rows604-results.ko.md) 605에서 직전 표시 뱅크 이력으로 첫 BG 48 B를 골랐다. 전체 ROM 읽기 단축은 두 위상에서 0.121–0.145 ms였고 954의 60 Hz 마감 전 ROM 공급 상한은 8/272 B였다. [605 근거](docs/nes-prefix605-results.ko.md) 606에서 954의 현재 캡처가 272/272 B를 보존했다. 이전 ACK 대기에 입력 6블록을 옮겨도 첫 E9는 EA 뒤 16.852 ms다. 입력을 전부 숨긴 조합에서도 필수 드라이버 비용까지 16.162 ms가 걸렸다. [606 검증](docs/nes-overlap606-results.ko.md) 607의 MMC577 ARM 후보는 최근 두 슬롯을 재사용해 Flash 16 B를 남겼다. 두 위상 53화면에서 밀집 25→24 VBlank, 마지막 ACK −17.799/−50.809 ms였다. 952·954의 SPI 거래는 증가했고 957 최종 대기는 0→1회여서 실기 기준은 MMC577이다. [607 검증](docs/nes-planner607-results.ko.md) 다음은 952·954의 추가 E8 조회와 실제 ROM 허가·credit 변화를 대조해 전송량과 마지막 payload 시각을 함께 줄이고, 957의 마지막 DMA와 검사선을 맞춰 최종 대기 0회를 복구하는 일이다.

- [597 결합 예산·핀 전송](docs/nes-region597-results.ko.md). 597은 595 핀 경로에서 묶음 전송으로 905·906 각각 97거래·698 B를 줄였다. 결합 진단은 2,625 LE로 809 LE 초과, 외부 생산 비용을 0으로 둬도 1,909 LE다. 다음은 MMC577 collector가 값을 확정하는 시점과 기존 SPI 페이지를 기준으로 중복 source 본체를 통째로 대체할 경계를 정하고, 입력 절감 뒤 남는 출력·최종 ACK 시간도 함께 예산화하는 일이다.

- [596 페이지·회로 예산](docs/nes-pages596-budget.ko.md). 596의 한 페이지 예약 방식은 입력당 26페이지·고정 78거래·546 B를 줄인다. 결합 진단 MAP은 2,708 LE로 892 LE와 새 제어 비용이 남았다. 다음은 NES 값/래스터/헤더와 SPI 응답 본체의 추가 순삭제 예산이다.

- [595 D4 source·SPI 결과](docs/nes-region595-results.ko.md). 594 ARM과 실제 입력 RTL을 연결했다. Lite 동일 경계 3,041 LE로 1,816 LE 선별 상한을 초과했다. 다음은 D4 명령 CDC·주소·CRC·패킷 묶음의 삭제/전송 예산이다. MMC577 유지.

- [594 ARM 동시 통과](docs/nes-report594-results.ko.md). 594 전체 ARM이 212,064 B로 링크돼 928 B가 남았다. 같은 ELF에서 cold 905는 17.984 ms(CPI 2), 53입력·27수신 조건·3표시 ACK 조건을 통과했다. 종료 보고 때만 서식을 복원하며 기존 로그와 바이트가 같다. 다음은 실제 고정 행·nonmap FPGA와 D4 요청·CRC·STOP 경계를 검증하는 일이다. 실기 기준 MMC577.

- [593 전체 ARM 결과](docs/nes-receiver593-results.ko.md). 593 ARM04에서 cold 905는 CPI 2 기준 17.984 ms로 MMC577보다 2.105 ms 단축됐다. 전체 Flash는 213,140 B로 한도보다 148 B 크다. 같은 ELF에서 53입력·27수신 조건·3표시 ACK 조건을 검증했다. 다음은 실행 코드 배치와 순회수 가능량 검토다. 실기 기준 MMC577.

- [592 교체 경계](docs/nes-boundary592-results.ko.md) · 592는 실제 591 M4의 53입력을 재실행했다. 교체 범위 4,796 B→3,028 B 이하, cold 905는 새 문법의 71 B 절감 뒤에도 CPI 2 기준 54,767명령 순절감이 필요하다. 둘 다 설계 상한이며 실제 삭제는 0 B다. 다음은 같은 전체 링크·cold에서 동시 판정하는 ARM 교체 한 건이다. 실패 시 코드 배치·지원 범위를 재검토하고 FPGA/두 위상/실기판은 보류한다. MMC577·독립 검사·STOP·최종 ACK·메뉴를 유지한다.

- 591 / PR151 samebranch. FIRST docs/nes-roles591-results.ko.md + docs/nes-retrospective579-plan.json. SELECTpatch02/ARM02/test03/analysis03. Actual577M4 oldmapcodec/BEGIN/packet replaced8Bsummary+bitmap+D4/CRC16/repair;53input+18guardsPASS(single sealed Python endpoint,NOTFPGA). WholeFW214760(+1852),cap+1768 FAIL;BSSsame18592/receiver+40B/native_frames31904/gap4888beforecalleeIRQ. packet1434->2724,logical1112->960,request320,digest76,newlibgccpopcount40 allcharged. MAP_ACCEPT+D0 necessary afterrowEND so repair cannot race nonmap;590dense6.775 correctedactual-callIO7.121;CPI2inputcold20.089->21.609/warm20.186->15.866/dense21.162->16.241 NOTcycles/fulltimeline. STOPresetcuts/false summaryrepair/RAMcorruption checked;finalACK/EA unchangedruntime consumedfixture only. REJECT591/noFPGAimplementation/MAP/FIT/twophase/ZIP becauseARMgatefailed;MMC577/READMEunchanged. NEXT actualoldnonmap/record+newphaseidentitycontrol deletion/wholeFlash budget before anynewprototype;no591adapter/CRC/helper/opcode/seedtuning or589generic revival. Quartus notmeasured!=zeroarea.

- 590 / PR151 samebranch. FIRST docs/nes-roles590-results.ko.md + docs/nes-retrospective579-plan.json. SELECTanalysis04;53pinned map reconstructions/20reference guards;existing577M4 CRC32 update256cases PASS(20B+already-linked1024Btable,6instructions/update NOTcycles). ARM-owned same/shift via8B whole-rowCRC32+first/last replaces16B tripleCRC;FPGA no previousbase/shiftdecision. Batched HELLO+REQUEST costs explicit: dense IO14.066->6.775ms,warm13.294->6.520,cold13.223->12.353;repair+8.716ms pluscompute. CRC16 reuse+samecanonicalCRC counterexample confirmed;retain freshCRC16/semantics/coverage. NOnewRTL/link/MAP/FIT/fulltiming/ZIP;netLEunknown/MMC577 unchanged. NEXT bounded8B/maprequest actualdeletion+packet/BEGIN/nonmap ownership and paired ARMlink/localMAP feasibility gate(netFlash<=84B,netLE<0,scratch<=1M9K),onlythen two-phase fullpath;notR3selected. oldlogical1112B retained=>packet-only replacement1518B arithmetic ceiling,not2630. No16B/perrowrequest/589generic/FSMtuning;READMEunchanged.

- 589 / PR151 samebranch. FIRST docs/nes-source589-results.ko.md + docs/nes-retrospective579-plan.json. SELECTtest02/map02/analysis02. Actualsource3072x8RAM+CRC+69bitbeatmailbox+single256BhostD0-D3:53frames282packets/8guardsPASS. LiteMAP1668->4014LE(+2346),comb1311->3517/FF794->1370/RAM2048->26624. M9K inferred;sourceFSMnotextracted/dynamicreturn+width/address remain. REJECT589/stophigherARM;noFSMattribute/opcode/seedloops. map01refwrongdefaulttimeout corrected33554432;candidateunchangedreused. NEXT ARMrowdecision+FPGAfixedsummary/request fullcost audit,notnewABIselected. R3false/MMC577/README/ZIPunchanged.

- 588 / PR151 samebranch. FIRST docs/nes-source588-results.ko.md + docs/nes-retrospective579-plan.json. SELECTanalysis03;53pinned sourceRAM references exact586 packets/restore,8STOP/commit/epoch guards,one256Bblock stalls. Dense I/O14.066->4.156ms only optimistic wire+503driver;oldnoninput59.983/59.989ms,NOTnewFPS/60Hz. Regionold1433LE+148=>1581LElimit;additional3M9K;ARM1434+1112+84=>2630Bceiling,NOTsaving. NEXT one boundedR2 source-first actualports/CRC/bytebeat/STOP/epoch +sameboundarycost;onlyifpass directARMreplacement/full212992link/fullstack,thenretimedtwo-phase. Nooutputhistory/commonresponse/codecvariants/wholeFITyet. MMC577/R3false/READMEunchanged.

- 587 / PR151 samebranch. FIRST docs/nes-ownership587-results.ko.md + docs/nes-retrospective579-plan.json. SELECTcheck03;455actualM4values/4admission/22controls PASS;2queryCRC reference counterexamples.6pinned577files prove SINGLE256Bsealed source+96bitmailbox, NOT584/586modeled4packet ring. CRC hostpackbytes!=NEScanonical;countacceptedqueryindex once. Oldlogical1136 deletion leaves276Bbefore replacement/history;RAM2124beforecallerIRQ/integrity. FullC expansion frozen/R3false. NEXT narrowed577input source+directARM paired deletion/port/cycle budget;retaintransport/output,noARM-onlyselection/noadapter/FITloops. MMC577/README/ZIPunchanged.

- 586 / PR151 samebranch. FIRST docs/nes-combined586-results.ko.md + docs/nes-retrospective579-plan.json. SELECTpatch02/ARM02/test03. ActualM4 section/row+canonicalCRC/direct50Bplan/shared259BRX;53inputs/15parserrejects/4slices/18transportrejects/3APIguards/7E9suffixcuts/4creditpressurePASS. FW213852(+944vs577/+500vs584),860BoverBEFOREhistory/planner/retainedbankintegrity;BSS18940/sliceStack832notfullIRQ. REJECTcomposition/stophistoryexpansion. Native+652B vs584 whileplan-98/runtime-30;newparser1530/row246/valueCRC208 +oldlogical1136 remains. NEXT checkownership decision:actualencodedBEGIN/logicalcontrol deletion with all semantic/CRC/required/STOP/ACK checks mapped;nofree1112Bcredit/noanotheradapter/padding/poll/log/FITloops. NoR3/FPGA/newFPS/ZIP;MMC577/READMEunchanged.

- 585 / PR151 samebranch. FIRST docs/nes-ownership585-results.ko.md + docs/nes-retrospective579-plan.json. SELECTanalysis05. Actualobject/DWARF1434Bpacket+166Badapter replacement;retain1112Bsemantic/68Brequired;after248Browkernel/360Bexcess,newcodeceiling992B NOTnetdeletion. Full8948Bhistorycannotfit4928/4852BprecallerIRQgap. Hybridexistingprefix+2297Bshadow+140Bstale+259BRX+8Bchunk=2708Baligned,2144BleftbeforecallerIRQ/identity/integrity.106tracechecks,densenet675B vs707.2Bexact;mask-onlycorruptioncounterexample;E9cut1..5naivepaddingclobberssuffix. Combined254Binput53reconstruction/maxDD<=259,notactualtransport. NEXT oneboundedcombinedARMlinkcost/integrity/ownership within992Bceiling/full212992cap+realstack;noFPGA/FIT/R3/FPSyet. MMC577/noZIP/READMEunchanged.

- 584 / PR151 samebranch. FIRST docs/nes-transport584-results.ko.md + docs/nes-retrospective579-plan.json. SELECTpatch02/ARM02/test07. Actual linkedM4 transport removesD0/D2/E0/E8;4paired951/954 boundedcases+18rejects/source4ring/output4credit pressure. Calls86..120->57..71 butwire+841..919B;FW213352(+444)/cap+360,BSS+84/observedstack+256. Driver259B mirrored:actualcapturesmax259,advertised255/256payloadfails260/261. NoactualIRQ/ROM/65816/two-slot/VBlank/nextgeneration concurrency. REJECTtransport-only/R3false. Current577pollstartsafterdisplayACK/EA,not498overlap. NEXTcombinedsection-rowdecoder/directprogress/SPI RXownership actualdeletion+Flash<=+84/RAM/historybudget BEFOREnewimplementation;no584padding/poll/Flashlog/FITloops. SourceCOMMITbase vsdisplayACKhistorydistinct. MMC577unchanged/noZIP/READMEunchanged.

- 583 / PR151 samebranch. FIRST docs/nes-row583-results.ko.md + docs/nes-retrospective579-plan.json. Same-row33 ±1 exactreuse951749→23/954755→75/957754→31words;inputdense1500.2→946.6B before newprotocol. SELECTarm04/analysis04/progress02;M4standalone248B/104stack/1537rows+17atomicrejects,notproduct;minimum164B deletionneededbeforeothercode,net0.50Bprecommandoutputsnapshot6normal20rejectsREFERENCEONLY. Fixed292B FETCHpadsinputdense1846.4B;variable2DMA/38Boverhead1092.4B +36Bfinalconfirm. C optimistic3queryIO10.507/10.517ms,95411.589/11.638,oldquerycount36.994/36.880ms;NOTnewtiming/R3. NEXT boundedactual577ARM transport ownership+source-ready/finitequeue/consumption/plan/IRQ,actualD0/D2/E0/E8deletion+netlinkFlash/stack/RAM;sourceinputCOMMITbase vsdisplayACKhistorydistinct,oldEA/newCOMMITgatepreserved. Cretainedintegrity/producer8948Bhistoryunfunded. No furtherrowcodec/fixedpadding/pollsize/FITloops. MMC577unchanged/noZIP/READMEunchanged.

- 582 / PR151 samebranch. FIRST docs/nes-abi582-results.ko.md + docs/nes-retrospective579-plan.json. R2 참조ABI A/B/C 모두R3미선정. C 밀집wire11.807/11.829ms지만503호출평균포함직렬IO16.454/16.485ms,954 20.813/20.643ms(실측/새전체시간아님). 53입력복원·8B stale합집합map복원/17정상10거절참조검사. source base2336B≥3M9K·producer nonmap cache/retained-integrity·실제순삭제미확보. NEXT951/954 base주소변화+독립D0/D2/E0/E8를대체할트랜잭션진행응답을같이설계,identity/CRC/padding/STOP/RAM포트포함. 582packet/poll변형·전체FIT반복금지. 제품/실기MMC577유지·Flash84B/LE148/M9K5·순삭제0·새ZIP없음.

- 581 / PR151 samebranch. FIRST docs/nes-body581-results.ko.md + docs/nes-retrospective579-plan.json. R1 마감(물리capture/NES진행/입력지연·밀집ROM/대표장면결측명시),다음R2 결합ABI·실제삭제·RAM포트예산. 53sealed입력/106D1경계/3378E1 publish-load-ACK 대조. 입력map1914→2571.88B,출력map96.8%같지만whole packet재사용0;reuse+재포장밀집4118.8/4122B>3937.5B(새검사/조회/gap전). inputsection/block+map소비 공동교체우선,514/515 재순회/국소poll재개금지. 순삭제0/FW·RTL·SDC·FIT·전체sim·ZIP없음/MMC577유지. analysis/body581-verification.json;로컬278파일evidence01.zip해시공개.

- 580 / PR150 병합588fa177ed1a82056a5cc86813506c3f2024cc70 확인. codex/nes-whole-budget-580. FIRST docs/nes-whole580-results.ko.md + docs/nes-retrospective579-plan.json. R1 기존자료 분석완료/누락계측전. MMC577 고정,75FPGA입력/414ARM파일 manifest,104간격 합계일치. 907–957 평균70.477/71.125ms,SEAL뒤DMA .993/.996ms,출력→SEAL21.632/21.669ms는 모델. D2 final start 로그덮어쓰기만수정/8조건 state동일;raw불변/SPI전체span null. NEXT 한차례 section본문·변경량·generation/준비/SEAL/ACK 연결 및 계측비용;R2 전체예산전 국소최적화금지. 제품RTL/FW/SDC/새FIT/전체sim/ZIP없음. 579가아래역사NEXT보다우선.

- PR150 / 579 회고·계획만. PR149 master병합6094a7cff6995981bea4f55be7f4ce6e27a81e06 확인. docs/nes-retrospective579.ko.md + docs/nes-retrospective579-plan.json FIRST;499/504의현재NEXT를대체. 실기MMC577 13.95fps/5–55초13.86fps고정. 조회D0/E0/E8제외관측wire18.18ms(현재작업량투영),60Hz전체예산미통과. R0완료/다음R1기존자료전체비용표→R2구조·실제삭제예산→R3한후보→R4실기. R2전국소DMA/poll구현금지. STOP·독립검사·최종ACK·VBlank·메뉴보존;양수timer/epoch/seed반복금지. 이번제품소스/합성/시뮬레이션/ZIP변경없음.

- 현재 522 / PR143. docs/nes-tail522-results.ko.md와 analysis/tail522-verification.json을 먼저 읽는다. MMC520 유지. 두 위상의 53개 RGB·표시 ACK 재현. 다음은 닫힌 VRAM 명령 선행 실행, 필요 시 수락된 map 분할 및 STOP·VBlank·전체 일정 검증.

- 521 실기 / PR142. docs/nes-hardware521-results.ko.md와 analysis/hardware521-mmc520.json을 먼저 읽는다. MMC520 실기 718표시/60.07초/11.95fps, 실행·메뉴 복귀 정상. 1–40초 12.08fps / 40–60초 11.60fps. 다음은 OBJ 소비 이후 출력·VBlank·ACK 비용 분리.

- 516 전달 기록 / PR141. docs/nes-window516-results.ko.md, analysis/window516-package.json, docs/nes-mmc516-trial.ko.md를 먼저 읽는다. 실기 기준 MMC509 12.82fps 유지. 결합은 같은 두 위상에서 후반 약 93.11→83.26ms. MMC516 trial02 전달 후 실제 SMB3 플레이·메뉴 복귀·새 로그 3개 확인 대기. ROM/save/RESTORE 미포함.

- 515 기록 / PR141. docs/nes-history515-results.ko.md와 analysis/history515-verification.json을 먼저 읽는다. MMC509 실기 12.82fps 유지. 기본 일정에서 직전 뱅크 행 이력으로 1,856B를 생략했으나 916 최종 ACK는 공통 코드 대조군과 같은 시각이었다. 두 시작 위상의 후반 간격과 제한을 결과 문서에서 확인한다. 다음은 MMC509 section 5 소비·SEAL 준비와 남은 VBlank의 시간 예산이다.

- 514 기록 / PR141. docs/nes-trim514-results.ko.md와 analysis/trim514-verification.json을 먼저 읽는다. MMC509 실기 12.82fps 유지. 8B 마스크·부분 DMA는 12화면에서 E1·DMA 각각 4,800B 절감, 후반 평균 93.110→104.826ms 회귀. 바이트별 CRC 재순회 후보는 종료한다. 다음은 최종 ACK에서 확정한 독립 뱅크·행 이력의 생성·조회·STOP 비용을 산정한다.

- 513 조사 / PR141. docs/nes-map513-results.ko.md와 analysis/map513-verification.json을 먼저 읽는다. MMC509 71화면 중 cold 뒤 동일 행 0/1763. 전체 행 이력은 보류. 8B 그룹으로 기존 map 패킷 양 끝만 줄이면 후반 전송량 −502.38B/화면, wire 환산 −1.531ms. ARM 커널 148B/마스크 192B이며 실제 표시 이득은 미측정. 다음은 Flash 36B 한도에서 기존 코드 대체 및 65816 bank·행 유효성/STOP/최종 ACK와 실제 일정 검증.

- 512 실행 기록 / PR141. docs/nes-transfer512-results.ko.md와 analysis/transfer512-verification.json을 먼저 읽는다. 실기 MMC509 12.82fps. 입력은 후반 10간격 합 0.030ms 절감·setup −0.317ns, map은 합 149.736ms 회귀, 결합은 116.445ms 회귀·Flash 0B. 두 후보는 보류. 다음은 대상 뱅크의 동일 map 행을 기존 literal DMA에서 실제 생략할 수 있는 양·시간·RAM 예산 조사.

- 511 계측 기록. PR140 병합 확인 후 codex/nes-output-budget-511 / PR141. docs/nes-output511-results.ko.md와 analysis/output511-verification.json을 먼저 읽는다. 최신 실기 MMC509 12.82fps. 다음은 map 직접 복원·입력 generation 공유의 분리 구현 및 네 가지 연속 일정 비교다. 재생에서 일반 소비 22.66ms, VBlank 대기 20.00ms. Flash 36B, FPGA 244LE·5M9K 예산 및 독립 검사·STOP·최종 ACK를 유지한다.

- 이전510: FIRST docs/nes-hardware510-results.ko.md + analysis/hardware510-mmc509.json. PR140, 실기 MMC509 60.08초/770표시/12.82fps·실행/메뉴 정상·체감 소폭. 502 10.59fps 대비 관측 +21.05%, 같은 동선/첫레벨 전용 가속률 아님. 수신19.88/계획14.30/출력43.17ms, 대기 위치 이동·중첩 주의. 마지막771번째 ordinary credit deadline 1/2/2·pending4; 전달 ARM03 5조건/18반례, 새 화면 제외. NEXT 출력 소비·DMA·최종 검사·VBlank 분리 + 남은 입력 본문 예산. 502 백업·STOP/독립 검사/finalACK 보존; 새 ZIP/FIT 없음.

- 509 제작 시점: docs/nes-service509-contract.ko.md + analysis/service509-verification.json + analysis/service509-package.json. PR140동일branch/실기MMC50210.59fps유지. E8공유34+40guards/12RGB PASS;508시간이득유지/FW212956 Flash36 BSS18576(+4vs502),stack24B회복. 실제bootCPU·PPU·MMC3 20frame 무선행/포화2386reads·선택4화면동일/STOPguardPASS. 8window재생은첫레벨폐루프아님.507 Lite15164LE51M9K setup+.078 hold+.139재사용/새FIT없음. MMC509 trial01 ZIP/ARM03은ARM01의784함수동일,label만509;ROM/save/RESTORE없음. NEXT 사용자실기3로그/같은동선502비교→수신·계획·SEAL/capture분석→A2본문예산. E8/phase/seed미세조정동결;fullCDCIO/IRQstack/60fps미완료.
- PR139 merge46c0cc962397b3e757c838164b70b75fe73090a6 및head afbd887의origin/master도달·tree일치를확인했다. 당시 브랜치 codex/nes-bandwidth-dma-budget-504 / PR140. 504 이력은 docs/nes-budget504-contract.ko.md + docs/nes-budget504-plan.json + analysis/budget504-verification.json. 실기502/503는유지. A2전체60Hz gate는미통과;수집정확성수정을되돌리거나기존498을자동승격하지않는다.
- 504 보존 기록(현재 경계·NEXT는506으로 대체): unchanged65816 PC계측으로cold502/과거12연속fixture의pixel·최종ACK시각동일. 연속평균SEAL→upload2.24ms/upload→ACK23.65ms,실기warm시간아님. 조회제외5911.51B/표시,12ms예산까지1974.01B부족. 공통generation Python332record17→15packet/604payloadB·642wireB차이/5반례;RTL·ARM미구현. 전체7533B이력cache최소7M9K>잔여5기각. NEXT packet완료뒤불변dirty-prefix만비차단inactiveVRAM DMA;mutable tail·부분VBlank·STOP이력무효화·최종검사/ACK유지. 목표추가SNES≤512B/WRAM≤8B/newM9K·ARM·FPGA제어0,실측아님. cold01/sequence01 raw근거probes/nes-budget504/evidence. 새FW/FIT/Questa/ZIP없음;RESTORE미포함정책유지.
- 이전 실기502/분석503: docs/nes-hardware503-results.ko.md + analysis/hardware503-mmc502.json FIRST.60.07초636최종표시10.59fps/94.45ms;실행·메뉴정상·사용자체감개선.4939.57 대비관측+10.61%,동일장면인과율아님.수신22.14/계획31.32/SEAL40.27ms;중첩op/quiet합산금지.보존history8전이fetch오류0,mask0거부4/회복4;전체capture건강·거부율미증명.실제502linked guard deadline1/window2/sink2·4조건/16반례,마지막637번째미완료제외.새FW/ZIP/FIT/Questa없음.비용50215287LE/121LE여유/Flash148B유지. NEXT A2본문·framing·늦은DMA예산;조회제외wire18.02ms,단순polling/FSM재개금지. 이전제작snapshot는불변.
- 현재500 A1 원인 분리: 실제493 PPU/collector9파일과179 PPUMASK/2006 기록으로24조건,정상15/거부9·01/04/06 재현·raw11776pixel 일치. 이전행pending과재개load/read 불일치가전체frame 거부로전파됨. 실제CPU/MMC3/PSRAM/게임/실기원인전체증명아님. test01 library누락/test02 fixture ALE/data-valid오배선 제외;선택test03/trace01/phase01. NEXT 행identity+완전raw coverage 뒤에만불완전fetch 회복,실제주소/data-valid/ROM fault/누락pixel/capacity/STOP 유지. 제품RTL수정·A1완료·새Lite/ZIP/FPS 없음.
- 이전 정상 실기493:60.07초575최종 표시9.57fps/부팅50ms·메뉴 정상,첫 레벨 차이 작음.4899.60fps와 다른 입력이라 지속 가속 미확인. 정상489 FPGA/SNES byte동일+491 ARMquery만 유지,Flash148B/whole15272LE51M9K. 마지막SEAL result1/window3/sink2는실제linked493 postguard/IO구분+16negative로검증;미완료1건은표시제외. 새SNESword/492FPGA보류·단일부팅원인미확정,493·489원복/GBC/save보존.
- 최신498: docs/nes-prefetch498-contract.ko.md + analysis/prefetch498-verification.json. END 수락+drain은IDLE 시작만,진행은lease/END로유지;ARM 최종ACK 대기중next input COMPLETE까지만수신,old video identity/EA뒤새COMMIT. linkedM4정상+5negative/728B callback stack,실제END/lease/exporter4mutant,고정MMC3 C/RTL/old65816 2표시68ACK4bulk/STOP·ACK12→EA12→COMMIT13 PASS;공통M4/IRQ 시간·게임FPS증명아님. 최초continuous-drain 취소결함검출/수정. Lite15132LE14105comb8394FF51M9K/잔여276LE/관련setup+.084hold+.147ns,Flash8B;loader WRITE late blocked선택512조합+mutant동등성. live보드와cost보드는이조건식만다르며hash/동등성고정. 실기4939.57fps/README/원복유지·새ZIP없음. 현재 NEXT는499 A1: 실기 fetch01/04/06의 low/high·PPUMASK·주소/load 짝과 raw-row 경계를 재현한다. 수집 거부를 성능 분석에서 누락하지 않는다. status/word/FSM 미세조정은499의 재개조건 전까지 보류.
- 직전497: docs/nes-bulk497-contract.ko.md + analysis/bulk497-verification.json. linked493 M4 12frame×3 소비지연/9negative PASS,219plan→32chunk/2bank;FINISH all-consumed/표시ACK 없는 retire 거부. instructionclock 모델이며실제65816/IRQ/ROM 공통시간은미완료. reader_drained=arb_idle은END 아님:다음export는generation-bound END 수락+drain,새COMMIT은old 최종ACK/EA뒤. 소유권조건확정후공동연결;실기493/합성비용유지·새ZIP없음.
- 직전496: docs/nes-schedule496-contract.ko.md + analysis/schedule496-verification.json.219 plans→32기존RTL묶음/3824B·583→396packet 모델교정,12동일픽셀/4조건PASS;657.420ms는새성능성과아님. 실제lease RTL은다음capture허용/export는old retire까지차단,stale/STOP+early-export mutant거부. ARM-only prefetch불가. S9 진행중:실제M4 complete485 단일bulkPending/E8/E0·ROM/IRQ 공통시간미연결;다음export시작과COMMIT 분리+oldidentity/guard소유권부터검토. 실기493유지/새합성ZIP없음.
- 실험495(cb09b33):EB8B 진행응답/마지막E0 fullACK+ROM request 중복gate삭제. M4 12기존/6negative·queue3x3949·ROM2위상/4096fault·C/RTL/old65816 1표시34ACK/STOP 통과. Lite15121LE14097comb8394FF51M9K(LE-151은packing,comb+19)/관련setup+.046hold+.164ns,Flash96B/RAM동일. 같은12frame .002794ms 절감/4ms위상 .013316ms 회귀:실제M4 busy-poll/IRQ/sourceROM·coalesced chunk가없어전체가속미증명. 실기493유지/새ZIP없음. NEXT 실제M4 polling+tile_bulk206 묶음+65816 공통event ledger;표시대기중receiver재사용은old identity·retire/STOP·재진입 없는SPI 소유권부터검토,추가작은opcode/seed루프금지.
- 개발 후보491:local plan append 중복 E8 제거+seed2B/64B bounded word DMA·MVN.71 actualCPU 표시3903.397->3620.517ms(7.25%),12/4ms시작/reset·108단위·M4 12guard/8burst/71state·joint/5124bus PASS. Whole Lite15272LE/51M9K·관련setup/hold+0.183/+0.168ns 동일,ARM Flash148B/emit stack16B. 물리 ARM/IRQ/ROM 공통시간 미증명. 492 부팅 실패로 새 FPGA/SNES 선택은 보류하며,493 부팅 회복 확인 뒤 전체 일정/D0를 검토한다. 현재9.57fps와이전489 실측을보존한다.
- 현재 개발 선택은489 실기 동작 경로다. loader inactive payload 선행 저장은 실제 쓰기/오류/STOP/drain 허용과 분리했으며 owned pins/control 동등성+3negative 통과. raw는 plane/row-major 전송과 실제 strided VRAM DMA,2B implicit-pattern cache+6B frame context를 사용한다. 인증은 변경 전 무효화하고 성공 표시 commit에서 확정한 뒤 ACK를 발행한다. 동일12개823.806->757.253ms,71개4234.845->3903.397ms는 실제65816+wire 모델이며 물리 FPS가 아니다.
- Whole Lite1회15272LE/14078comb/8392FF/264800logicalbits/51M9K;136LE·5M9K 여유. 관련 setup+0.183/hold+0.168ns,nominal+0.224/+0.168ns.5KiB ROM이3M9K를 회수한 것은 아니다. ARM493 Flash148B(이전489124B)/새 global0B/RUN31848B/full stack·IRQ 미증명, SNES body4311B/문맥8B. 새 false-path/seed loop 없음, 전체 reset/CDC/IO 미승인 유지.
- MMC489-RAWDMA.zip은 probes/nes-output489/trial02;현재FPGAboard02/ARM02/client04(시험03과동일) 선택, marker NES MMC3 489.nh1/ROM mmc489.nes/로그 *-mmc489.txt. 수신490에서 실행·메뉴 복귀/60.08초577회9.60fps 확인,첫 레벨 체감 개선 작음. 먼저 docs/nes-hardware490-results.ko.md + analysis/hardware490-mmc489.json을 읽는다. NEXT E8공급/E0소비credit·ACK/65816검사 일정 공동 추적,그다음D0 source/ROM.485 대기13.55/플레이8.22와 동일 장면 가속은 미입증. C/RTL boot join은 raw0,raw71 CPU시험과 공통 물리 시계로 합치지 않는다. MCU_RDY는 external_memory_ready이지 source-ready IRQ가 아니다.
- 추가·공개 완료는 GB/GBC G13C44/0.9.0뿐이다. NES60fps는 미완료이며 문양476의23.84fps는 별도 회귀다.
- 현재 실기 근거는 `analysis/hardware510-mmc509.json`,이전502는 `analysis/hardware503-mmc502.json`,이전493은 `analysis/hardware494-mmc493.json`,이전489는 `analysis/hardware490-mmc489.json`,이전485는 `analysis/hardware486-gameplay485.json`, 문양 회귀는 `analysis/receive477-hardware.json`, 인계는 `cores/nes/HANDOFF.ko.md`다.2차 video_error13의 deadline/emit 전파는 슬롯1/128 실제 M4 시험으로 검증했으며 진짜 capacity 실패를 포괄 허용하지 않는다.
- `src/fpga`, `src/firmware-overlay`, `src/renderer`의 검증된 GBC와 사용자 저장·복원물을 보존한다.

## 문서와 PR

- 사용자 백업 정책(502 수신): 다음 NES 시험판부터 RESTORE 폴더/이전 버전 복구본을 새 전달 ZIP에 넣지 않는다. 기존 ZIP·백업은 삭제하지 않고 실행상의 STOP/base/menu 복구는 유지한다.

- PR 본문과 `docs/progress/pr-NNN.md`는 반드시 **목표 → 작업내용 → 성과 → 후속작업** 네 절을 사용한다. `.github/PULL_REQUEST_TEMPLATE.md`와 운영 규칙도 같은 이름이다.
- README는 의미 있는 진척 변화나 정정이 필요할 때만 갱신한다. 작은 작업마다 수정하거나 PR별 요약을 누적하지 않는다. 일상 진행·PR별 결정은 progress 폴더에 기록한다.
- 새 결과는 후보·구성·장면·조건·근거를 함께 연결한다. 실기 FPS, 모델 시간, 명령 수, MAP, FIT/STA를 섞지 않는다.
- 미구현·기각 후보를 현재 제품으로 표시하지 않는다. 다른 구성의 최소 시간/면적을 합친 성공을 만들지 않는다.
- 같은 근거를 여러 곳에 새 원문으로 복사하지 말고 검증 JSON·계약으로 연결한다. 현재 등록부는 짧게 유지한다.
- 사용자가 PR/문서 정리만 요청하면 그 범위만 처리한다. 공개 PR 병합·릴리스·장치 설치는 자동 실행하지 않는다.

## 개발·검증

- 작업 브랜치 접두사는 `codex/`. 사용자 병합 보고 뒤 실제 master 도달 관계를 확인한다. 기존 작업을 reset/rebase로 버리지 않는다.
- 변경 경계에 필요한 최소 검증을 한다. 변경 없는 전체 적재·합성·기존 복원/GBC 시험을 반복하지 않는다.
- NES에서는 독립 CRC/coverage, 4credit와 실제 소비의 구분, STOP·stale DONE/ACK 차단, 최종 표시 ACK 뒤 commit/EA retire, base/menu 복구를 유지한다.
- 현재 회로는 export COMMIT 뒤 다음 capture를 이미 시작한다. 중첩을 새 성과로 계산하거나 이전 표시 중 ARM receiver를 덮지 않는다.
- 남은 수신/CRC와 capture/export/표시 시각을 먼저 분리한다. 근거 없이 범용 실행기·queue 수·작은 FSM을 반복 교체하지 않는다.
- Quartus는 **Lite**를 기본으로 사용한다. Standard 구매/평가 재시도는 자동 진행하지 않는다.
- Questa는 설치된 Starter FLOAT **1좌석으로 순차 실행**한다. 기존 허가된 wrapper를 사용하고 점유 포트/다른 작업 서버를 침범하지 않는다. 새 실제 오류가 없으면 라이선스 smoke를 반복하지 않는다.
- 라이선스 파일·signed FEATURE/INCREMENT·host ID·서버 로그는 Git에 넣지 않는다. 다른 PC에서는 해당 PC의 정당한 도구/권한을 준비한다.

## 파일·보고

- 검색은 `rg`를 우선한다. RTK가 있으면 큰 읽기 요약에 활용하되 ROM/ASM/정확한 diff·hash·실패 원시 로그는 필터링하지 않는다.
- 개인 절대 경로·채팅·Downloads에만 있는 정보에 의존하지 않는다. 로컬 자료 의존성과 실행 범위를 재개 안내에 명시한다.
- allowlist를 지킨다. `git add .`/`git add -f` 대신 검토한 경로만 등록한다. 상용 자산·save/dump·키·도구 캐시는 제외한다.
- 기존 원시 실패와 동결 산출물을 덮지 않는다. 새 전달본은 번호·marker·로그·설치/원복을 함께 갱신한다.
- 실기는 사용자가 설치 ZIP을 SD에 복사하고 로그를 돌려주는 방식이다. 알려진 보드나 SD/USB 연결을 다시 요구하지 않는다.
- 단계 완료·큰 변경·중요한 결과 위주로 간결하게 보고한다. 자세한 진행은 문서에 남기며 이미 허가된 범위의 작업을 반복 확인하지 않는다.

- 단순 NROM은 회귀 fixture이며 게임60fps의 선행 조건이 아니다.480의 공동 기능/픽셀 근거는 실물 SNES 부팅 증명이 아니다. 현재 게임 실기485 및 이전482와 문양476 약24fps 원복을 보존한다.481은 기각이며482 한 회 성공으로480 물리 실패 원인을 단독 확정하지 않는다. 같은480 재시험·계측만 늘리는 전달·근거 없는 FSM/seed/FIT 반복을 피한다.

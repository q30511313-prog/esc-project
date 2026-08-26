# FitFace Studio G-SHOCK LCD v11 Stable — 최종 인수인계

## 1. 상태

**v11 실기기 색상 및 기능 검증 완료 / 안정 기준본으로 승인됨.**

이 문서 이후 `fitface-v11-stable`은 v11 기준선으로 취급한다. 새로운 기능이나 실험은 이 브랜치를 직접 수정하지 말고 별도 작업 브랜치에서 시작한다.

## 2. 저장소 및 기준

- Repository: `q30511313-prog/esc-project`
- Stable branch: `fitface-v11-stable`
- Stable branch origin: approved v11 merge commit `bf2ee876d9acf99e2a25424900ed3314d4480cae`
- FitFace Studio upstream: `satvikgosai/fitface-studio`
- Upstream commit: `45a9788d3877627fd5301e9ebba36ef6192d7962`
- Application ID: `dev.fitface.studio.lcdcomposite.v11`

## 3. 확정 색상

### 사용자/UI 논리 목표색

- Hex: `#B8B8AD`
- RGB: `(184, 184, 173)`

UI에서 선택하는 목표색은 변경하지 않는다.

### Galaxy Fit3 / Samsung 00003 style3 실기기 보정

- Calibration selection: Patch 15
- Representative RGB888: `#B5B6BD`
- RGB565: `0xB5B7`
- R5/G6/B5: `22 / 45 / 23`

이 값은 Galaxy Fit3 실제 화면을 사람 눈으로 보고 선택·승인한 값이다. 카메라 사진의 화이트밸런스/톤매핑은 최종 색상 판정 기준으로 사용하지 않는다.

## 4. 실기기 승인 결과

Samsung stock watchface `00003`, black `style3` 기준:

- 시간 숫자 정상
- 콜론 정상
- 날짜 정상
- 배터리 정상
- 걸음 수 정상
- 날씨 정상
- 숫자가 검게 죽는 문제 없음
- style3 → 다른 스타일 → style3 전환 정상
- 실제 눈으로 본 LCD 색상 정상/승인

따라서 v11은 색상과 주요 표시 기능 모두 실기기 검증 완료 상태다.

## 5. 유지되는 기능

- Sequence 실험 기능
- Pair Binding 실험 기능
- Sprite LCD 색상 변경
- Pair / VALUE 색상 변경
- Composite 색상 변경
- Type-1 Static raster 색상 변경
- RGB565+A Sprite alpha-mask 처리
- Clock Sprite group 색상 처리
- Casio clock chrome tone 통일
- Samsung 00003 전체 전경 tone 통일
- Samsung 00003 style3 optical compensation
- Pair patch order normalization
- hardware non-sprite 색상 보정
- bright G-SHOCK LCD label
- 위치 / 크기 / 기존 편집 기능
- 스타일 전환 기능

## 6. 핵심 해결 사항 — 시간 숫자 검정 문제

원인은 일반 RGB565 색상값 자체가 아니라 Samsung 시간 SPRITE가 `RGB565 + Alpha` 구조이며 실제 숫자 형태가 Alpha에 저장되어 있다는 점이었다.

확정 처리 방식:

- `Alpha == 0`: 투명 영역, RGB 변경하지 않음
- `Alpha > 0`: RGB565 payload를 목표색으로 직접 교체
- Alpha byte는 원본 그대로 유지

이 처리로 숫자 형태, 안티앨리어싱, 투명 배경을 유지하면서 시간 숫자가 정상 LCD 색으로 표시된다.

## 7. v11 색상 보정 적용 순서

v11은 v10의 검증된 패치 스택 위에 좁은 하드웨어 보정 레이어만 추가한다.

1. 기존 sequence / pair / sprite / composite / static 패치 적용
2. Samsung 00003 foreground tone 통일
3. v10 optical baseline 적용
4. v11 Patch15 hardware calibration 적용
5. Pair normalization 및 hardware non-sprite fix 적용

v11 overlay:

`fitface-lcd-color/apply_samsung00003_clock_optical_v11.py`

- v10 optical red `0xB8` → v11 `0xB5`
- v10 optical green `0xC0` → v11 `0xB6`
- v10 optical blue `0xA1` → v11 `0xBD`

## 8. 정식 안정 빌드

Workflow:

`.github/workflows/build-fitface-v11-stable.yml`

Workflow name:

`FitFace Studio G-SHOCK LCD v11 Stable`

첫 안정 빌드:

- Run ID: `32998287909`
- Run number: `1`
- Trigger commit: `56b8a8e31e83a6d3fee86a77a9302ec7dce7f1c2`
- Status: `completed`
- Conclusion: `success`
- Started: `2026-08-26T18:10:57Z`
- Completed: `2026-08-26T18:16:45Z`

통과 항목:

- stock face non-sprite inspection
- stock face sprite payload inspection
- 전체 승인 패치 스택 적용
- focused format regressions
- editor unit-test regression suite
- `:app:assembleDebug`
- final APK existence / size / SHA verification
- Artifact upload

## 9. Stable Artifact

- Artifact ID: `9617643148`
- Artifact name: `FitFace-Studio-GSHOCK-LCD-v11-FULL`
- Artifact ZIP size: `13,597,282 bytes`
- Artifact ZIP SHA-256: `91f6c42a8bf04c6f8d1aa608840cd3245c76e56e6544534ff23805da7c1a2ce1`
- Created: `2026-08-26T18:16:42Z`
- Expires: `2026-11-24T18:10:58Z`

Artifact 내부 최종 APK:

- Filename: `FitFace-Studio-GSHOCK-LCD-v11-FULL.apk`
- Size: `38,004,422 bytes`
- SHA-256: `98e250c1ecc77f31e5cd798b69f0a870e6ae3b5d8716c970f1b124ef6658f1c0`

## 10. 이전 승인 APK와 stable rebuild 동등성 검증

실기기에서 승인된 이전 v11 APK:

- SHA-256: `259baf9476a013c7a049e8d918c09c4787ffba134abd0fcc073d511436e47074`
- Size: `38,004,422 bytes`

정식 stable workflow에서 새로 빌드된 APK:

- SHA-256: `98e250c1ecc77f31e5cd798b69f0a870e6ae3b5d8716c970f1b124ef6658f1c0`
- Size: `38,004,422 bytes`

두 APK를 압축 해제하여 내부 파일을 비교한 결과:

- entry count: `195 / 195`
- differing entry count: `0`
- 결과: **모든 195개 APK 내부 엔트리의 SHA-256이 동일**

따라서 전체 APK 파일 SHA 차이는 APK ZIP 컨테이너/빌드 패키징 수준의 차이이며, 앱 내부 콘텐츠는 승인 APK와 동일하다.

## 11. 브랜치 정책

### 동결 기준

`fitface-v11-stable`

이 브랜치의 app-producing helper/patch 값은 v11 승인 기준으로 동결한다.

### 이후 개발

새 기능, 구조 변경, 추가 보정은 반드시 `fitface-v11-stable`에서 별도 브랜치를 만들어 작업한다.

예:

- `work/fitface-v12-...`
- `feature/fitface-...`
- `fix/fitface-...`

검증 완료 전 stable에 직접 반영하지 않는다.

## 12. 하지 말아야 할 것

- `#B8B8AD` UI 목표색을 임의 변경하지 않기
- 승인된 `#B5B6BD / 0xB5B7` 보정값을 추측으로 다시 조정하지 않기
- Alpha-mask 원인 분석을 처음부터 다시 시작하지 않기
- 기존 정상 기능 삭제하지 않기
- Samsung 00003 style3 보정을 다른 스타일에 무분별하게 확대하지 않기
- 카메라 사진만으로 색상을 재판정하지 않기
- 16패치 calibration 실험 브랜치를 stable에 병합하지 않기

## 13. 다음 작업 시작 기준

다음 개발 작업은 **v11 색상 보정 프로젝트의 연장이 아니라, 이미 승인된 v11 stable 위의 별도 기능 작업**으로 시작한다.

기본 원칙:

1. `fitface-v11-stable`에서 새 브랜치 분기
2. v11 색상 및 기존 기능을 회귀 기준으로 고정
3. 새 기능만 TDD/회귀 테스트로 추가
4. 실기기 확인이 필요한 변경은 Fit3에서 최종 확인
5. 승인 후에만 stable 반영 여부 결정

# FitFace v12 Foundation Design

## 1. 목적

v11 Stable의 앱 동작과 실기기 승인 결과를 그대로 유지하면서, 현재 GitHub Actions 안에 흩어져 있는 패치 적용 순서를 **하나의 선언적 빌드 manifest + 단일 실행기**로 통합한다.

이 작업은 새 기능을 추가하지 않는다. 목표는 이후 v12 기능 개발에서 패치 순서, upstream 기준, 색상 잠금값, 회귀 테스트 범위를 한 곳에서 추적할 수 있게 만드는 것이다.

## 2. 기준선

- Stable branch: `fitface-v11-stable`
- Foundation branch: `work/fitface-v12-foundation`
- Stable app-producing baseline commit: `bf2ee876d9acf99e2a25424900ed3314d4480cae`
- FitFace Studio upstream repository: `satvikgosai/fitface-studio`
- Upstream commit: `45a9788d3877627fd5301e9ebba36ef6192d7962`
- Application ID: `dev.fitface.studio.lcdcomposite.v11`
- Logical/UI target color: `#B8B8AD`
- Samsung 00003/style3 approved hardware payload: `#B5B6BD`
- RGB565: `0xB5B7`

위 값은 Foundation에서 변경하지 않는다.

## 3. 현재 문제

현재 Stable workflow는 다음 정보를 YAML 안에서 직접 관리한다.

- upstream checkout ref
- helper/test 복사 순서
- sequence patch 적용 전 `sed` 변형
- pair patch
- sprite/pair/composite/static patch
- RGB565+A alpha-mask patch
- clock sprite group patch
- chrome/foreground/optical patch
- pair normalization
- hardware non-sprite patch
- app ID 치환
- 회귀 테스트 목록

이 방식은 현재 동작하지만, 새 기능이 추가될 때 패치 순서와 검증 기준이 workflow 여러 줄에 분산된다. 순서가 바뀌거나 한 항목이 빠져도 변경 이유를 추적하기 어렵다.

## 4. 선택한 접근

### 선언적 JSON manifest + Python 실행기

새 디렉터리 `fitface-build/`를 만들고 다음 책임으로 분리한다.

1. `v12-foundation-manifest.json`
   - upstream repo/ref
   - application ID
   - 잠금 색상값
   - 정확한 patch step 순서
   - 각 step에서 실행할 shell command 목록
   - focused regression test class 목록

2. `run_manifest.py`
   - manifest schema/필수값 검증
   - step ID 중복 검사
   - 고정값 검사
   - helper root / target root 변수 치환
   - command를 manifest 순서 그대로 실행
   - `--check` 모드에서는 실행 없이 manifest와 파일 존재 여부만 검증

3. `test_manifest.py`
   - Python 표준 `unittest`만 사용
   - upstream commit 잠금 검증
   - logical/optical/RGB565 값 잠금 검증
   - app ID 잠금 검증
   - exact ordered step ID 목록 검증
   - step ID uniqueness 검증
   - required helper script/test path 존재 검증

4. `.github/workflows/build-fitface-v12-foundation.yml`
   - Stable과 Foundation 두 개의 clean upstream checkout 생성
   - Stable checkout에는 기존 v11 legacy 명령 순서를 그대로 적용
   - Foundation checkout에는 `run_manifest.py`를 적용
   - Foundation checkout에서 focused format regression + editor regression 수행
   - 두 checkout 모두 `:app:assembleDebug`
   - 두 APK를 unzip하여 모든 내부 entry 이름과 SHA-256을 비교
   - 차이가 1개라도 있으면 실패
   - 동등성 통과 시 Foundation APK artifact 업로드

## 5. 왜 JSON인가

- Python 표준 라이브러리만으로 읽을 수 있어 PyYAML 같은 추가 dependency가 필요 없다.
- Git diff에서 patch 순서 변경을 명확하게 볼 수 있다.
- CI와 로컬 실행기가 동일한 source of truth를 사용한다.

## 6. Manifest 구조

최상위 필드는 아래 형태로 고정한다. 예시는 실제 허용되는 값과 command 형식을 보여준다.

```json
{
  "schema_version": 1,
  "upstream": {
    "repository": "satvikgosai/fitface-studio",
    "commit": "45a9788d3877627fd5301e9ebba36ef6192d7962"
  },
  "locks": {
    "application_id": "dev.fitface.studio.lcdcomposite.v11",
    "logical_color": "#B8B8AD",
    "optical_rgb888": "#B5B6BD",
    "optical_rgb565": "0xB5B7"
  },
  "steps": [
    {
      "id": "rgb565-alpha-mask",
      "commands": [
        "python3 {helper}/fitface-lcd-color/apply_sprite_alpha_mask_fix.py {target}"
      ]
    }
  ],
  "focused_tests": [
    "LcdSpriteTintTest",
    "Samsung00003ClockOpticalV11Test"
  ]
}
```

실행기는 `{helper}`와 `{target}` 두 placeholder만 지원한다. 임의의 환경 변수 확장이나 별도 템플릿 언어는 추가하지 않는다.

## 7. 정확한 Patch Step 순서

Foundation manifest의 step ID 순서는 아래와 같아야 한다.

1. `install-lcd-helpers-tests`
2. `sequence-foundation`
3. `pair-binding`
4. `sprite-pair-lcd-controls`
5. `rgb565-alpha-mask`
6. `clock-sprite-group`
7. `composite-color`
8. `static-raster-color`
9. `casio-clock-chrome`
10. `samsung00003-foreground`
11. `samsung00003-v10-optical-baseline`
12. `samsung00003-v11-patch15`
13. `pair-normalization`
14. `hardware-nonsprite`
15. `bright-lcd-label`
16. `application-id`

이 순서는 Stable의 앱 생성 순서를 그대로 표현한다.

## 8. 회귀 테스트 잠금

focused regression 목록은 Stable에서 사용한 다음 테스트를 그대로 유지한다.

- `LcdSpriteTintTest`
- `LcdPaletteTest`
- `CompositeColorOverrideTest`
- `StaticRasterTintTest`
- `StaticAlphaMaskTintTest`
- `AnchoredPairColorTest`
- `DuplicateSequencePairColorTest`
- `ClockSpriteColorGroupTest`
- `CasioClockChromeToneTest`
- `Samsung00003ForegroundToneTest`
- `Samsung00003ClockOpticalV11Test`
- `SequenceOverrideTest`
- `PairBindingOverrideTest`

추가로 `:feature:editor:testDebugUnitTest` 전체 회귀를 유지한다.

## 9. 동등성 검증

Foundation은 기능 변경이 없어야 하므로 단순히 테스트가 통과하는 것만으로 부족하다.

CI에서 같은 upstream commit을 두 번 checkout하고:

- A: 기존 v11 Stable legacy pipeline
- B: v12 Foundation manifest pipeline

으로 각각 APK를 만든다.

검증 조건:

1. 두 APK unzip entry 이름 집합이 완전히 동일해야 한다.
2. 각 entry의 raw bytes SHA-256이 모두 동일해야 한다.
3. differing entry count가 `0`이어야 한다.

APK ZIP 컨테이너 전체 SHA는 ZIP metadata 때문에 다를 수 있으므로 acceptance criterion으로 사용하지 않는다. 내부 entry 동등성을 기준으로 한다.

## 10. 오류 처리

`run_manifest.py`는 다음 경우 즉시 non-zero exit한다.

- manifest 파일이 없음
- `schema_version != 1`
- upstream repository/commit이 승인값과 다름
- application ID / 색상 lock이 승인값과 다름
- step ID가 중복됨
- step 순서가 exact expected order와 다름
- command가 비어 있음
- `{helper}` 또는 `{target}` 외 미지원 placeholder가 있음
- `--check`에서 required helper path가 없음
- 실제 실행 command가 하나라도 실패함

실패 시 step ID와 command index를 stderr에 명시한다.

## 11. Stable 보호 원칙

- `fitface-v11-stable`은 수정하지 않는다.
- Foundation은 `work/fitface-v12-foundation`에서만 개발한다.
- `#B8B8AD`, `#B5B6BD`, `0xB5B7`은 변경하지 않는다.
- 16-patch calibration branch를 포함하지 않는다.
- Alpha-mask 처리 로직을 재설계하지 않는다.
- 앱 기능/화면/UI를 변경하지 않는다.

## 12. 완료 조건

Foundation은 아래 조건을 모두 만족할 때만 완료다.

1. manifest 단위 테스트 PASS
2. manifest `--check` PASS
3. Foundation focused format regressions PASS
4. editor regression PASS
5. Foundation APK build PASS
6. legacy v11 baseline APK build PASS
7. 두 APK 내부 entry SHA 비교 `0 differences`
8. artifact 생성 PASS
9. `fitface-v11-stable` 대비 app-producing helper/patch 파일은 변경 없음
10. 변경 범위가 `fitface-build/`, Foundation workflow, spec/plan 문서로 제한됨

## 13. 다음 단계와의 관계

이 Foundation이 승인된 뒤 2단계 Release build 체계는 manifest pipeline을 재사용한다. Release 단계에서는 버전명/versionCode와 signing source를 별도 설계하며, Foundation의 색상/patch 순서를 수정하지 않는다.

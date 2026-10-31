# 캐릭터 자산 확인 기록

2026-10-30 확인. **사용 금지가 확인된 것이 아니라 기본 이미지의 외부 재배포 허가 범위가 미확인입니다.**

- OpenAI 공식 Codex 저장소에는 기본 펫 카탈로그가 공개되어 있습니다.
  [catalog.rs](https://github.com/openai/codex/blob/main/codex-rs/tui/src/pets/catalog.rs)
- Codex 저장소의 코드 라이선스는 Apache 2.0입니다.
  [LICENSE](https://github.com/openai/codex/blob/main/LICENSE)
- 위 사실만으로 별도 CDN의 이미지 파일까지 같은 라이선스로 배포할 수 있다고 단정하지 않았습니다.
- 공식 [Pets 설정 안내](https://learn.chatgpt.com/docs/app/settings)는 앱 안에서 기본·커스텀 펫을 선택하는 방법을 설명합니다.
  다른 앱의 저장소에 기본 이미지 파일을 함께 배포하는 허가로 해석하지 않았습니다.
- [OpenAI 브랜드 안내](https://openai.com/brand/)도 확인했지만 펫별 재배포 조건을 찾지 못했습니다.

기존 개인용 앱의 이미지나 동작은 변경하지 않았습니다. 공개 소스는 기존 9종 PNG 스프라이트 재생을 유지합니다.
이미지가 없는 경우에만 `companions.py`의 자체 도트 로봇을 임시 표시합니다.

## 자동 탐색과 대체 표시

앱 시작 시 각 펫별로 다음 위치만 확인합니다.

1. 앱 폴더의 `assets/<id>.png` (기존 로컬 사용 호환)
2. `CODEX_HOME/cache/tui-pets/v1/assets/<id>-spritesheet-v4.webp`
3. 같은 Codex 캐시 경로의 PNG 파일
4. Windows의 현재 사용자에게 설치된 `OpenAI.Codex` 패키지의 `app/resources/app.asar` 내부 펫 이미지

데스크톱 설치 위치는 Windows 패키지 조회로 알아내며 버전·사용자 경로를 고정하지 않습니다.
ASAR 헤더와 해당 펫 바이트만 읽어 메모리에서 표시하며 파일을 추출·저장하지 않습니다.
1536×1872 및 1536×2288 아틀라스를 지원합니다. 최신 규격의 추가 시선 행은 현재 연출에 사용하지 않습니다.
패키지 조회·파일 읽기가 거부되거나 번들 구조가 바뀌면 다른 로컬 후보 또는 로봇으로 대체합니다.

`CODEX_HOME` 미설정 시 사용자 홈의 `.codex`를 사용합니다.
[공식 캐시 경로 소스](https://github.com/openai/codex/blob/main/codex-rs/tui/src/pets/asset_pack.rs)를 기준으로 구현했습니다.
CLI 설치만으로 모든 펫이 저장되는 것은 아닙니다. 해당 CLI가 펫 사용 시 다운로드한 파일이 있어야 합니다.
Hoots처럼 CLI에 없는 펫도 데스크톱 번들에 있으면 표시됩니다.

WebP를 읽으려면 `python -m pip install -r requirements.txt`로 Pillow를 설치하세요.
이미지 없음, 읽기 권한 없음, 손상, 크기 불일치, Pillow 미설치 시 해당 펫만 로봇으로 표시합니다.
일부 펫만 설치되어 있으면 원래 펫과 로봇이 함께 등장합니다. 파일을 준비한 뒤 앱을 재실행하세요.
Codex 캐시의 원본 파일은 수정하지 않습니다. 앱 시작 시 네트워크로 이미지를 내려받지 않습니다.
전체 사용자 폴더를 재귀 탐색하지 않습니다. 향후 Codex 캐시 규격 변경 시 로봇으로 표시될 수 있습니다.

## 이미지 형식

`assets/<id>.png`를 사용하는 기존 렌더러입니다. 1536×1872 또는 1536×2288, 8열×9행 또는 11행, 셀 192×208 픽셀.
ID: `codex`, `dewey`, `fireball`, `hoots`, `rocky`, `seedy`, `stacky`, `bsod`, `null-signal`.
본인에게 사용 권한이 있는 파일을 로컬에서 배치할 수 있습니다. 이 방법이 별도 사용 허가를 제공하는 것은 아닙니다.
앱 시작 시 이미지를 자동 다운로드하지 않으며 `assets/`는 Git 제외 대상입니다.

Claude의 Clawd를 연상시키는 캔버스 캐릭터도 유지되어 있습니다. 직접 그린 코드와 별개로
브랜드 캐릭터로서의 외부 배포 조건은 확인이 남아 있습니다. 코드 라이선스가 브랜드 권리를 부여하지 않습니다.

**배포 방식:** 이미지 파일을 제외한 소스만 공개하고 사용자 PC의 기존 이미지를 읽습니다. 로컬 파일 읽기 기능이 별도의 자산 사용 허가를 부여하는 것은 아닙니다.
출처 표기만으로 권리가 확보되었다고 표시하거나, 이미지를 프로젝트 MIT 라이선스로 재허가하지 않습니다.

macOS에서는 `/Applications/Codex.app/Contents/Resources/app.asar`와
`~/Applications/Codex.app/Contents/Resources/app.asar`도 순서대로 확인합니다.
앱을 다른 위치에 설치했다면 기존 CLI 캐시 또는 로컬 assets 폴더를 사용하세요.
설치되어 있지 않거나 읽을 수 없는 앱은 건너뛰고 로봇으로 대체합니다.


## 버튼으로 기본 펫 받기

`펫 도감 → 기본 펫 8종 받기`를 누르면 공식 CLI가 사용하는
`https://persistent.oaistatic.com/codex/pets/v1`에서 Codex, Dewey, Fireball,
Rocky, Seedy, Stacky, BSOD, Null Signal을 받습니다. Hoots는 공식 CLI 목록에 없습니다.
다운로드는 사용자가 버튼을 누를 때만 시작하며, 세션 기록이나 인증 정보를 보내지 않습니다.
Pillow가 필요합니다. 파일별 4 MiB 제한, WebP 형식과 1536×1872 크기를 검증한 뒤
앱의 `runtime/pets`에 저장합니다. 정상 파일은 재사용하고 실패한 펫은 다시 시도할 수 있습니다.
다운로드가 완료되면 화면과 열린 도감에 바로 반영됩니다. 창을 닫아도 이미 시작된 다운로드는
앱이 실행 중이면 계속됩니다. 앱 종료 시 작업이 중단될 수 있으며 재실행 후 다시 시도할 수 있습니다.
다운로드한 이미지는 Git 제외 대상이며 코드 라이선스로 재배포 허가를 주장하지 않습니다.

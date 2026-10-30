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

`CODEX_HOME` 미설정 시 사용자 홈의 `.codex`를 사용합니다.
[공식 캐시 경로 소스](https://github.com/openai/codex/blob/main/codex-rs/tui/src/pets/asset_pack.rs)를 기준으로 구현했습니다.
CLI 설치만으로 모든 펫이 저장되는 것은 아닙니다. 해당 CLI가 펫 사용 시 다운로드한 파일이 있어야 합니다.
공식 CLI 카탈로그에 없는 Hoots 등은 해당 파일이 없으면 로봇으로 표시됩니다.

WebP를 읽으려면 `python -m pip install -r requirements.txt`로 Pillow를 설치하세요.
이미지 없음, 읽기 권한 없음, 손상, 크기 불일치, Pillow 미설치 시 해당 펫만 로봇으로 표시합니다.
일부 펫만 설치되어 있으면 원래 펫과 로봇이 함께 등장합니다. 파일을 준비한 뒤 앱을 재실행하세요.
Codex 캐시의 원본 파일을 수정하거나 앱 폴더로 복사하지 않으며 네트워크로 내려받지도 않습니다.
전체 사용자 폴더를 재귀 탐색하지 않습니다. 향후 Codex 캐시 규격 변경 시 로봇으로 표시될 수 있습니다.

## 이미지 형식

`assets/<id>.png`를 사용하는 기존 렌더러입니다. 1536×1872, 8열×9행, 셀 192×208 픽셀.
ID: `codex`, `dewey`, `fireball`, `hoots`, `rocky`, `seedy`, `stacky`, `bsod`, `null-signal`.
본인에게 사용 권한이 있는 파일을 로컬에서 배치할 수 있습니다. 이 방법이 별도 사용 허가를 제공하는 것은 아닙니다.
앱이 이미지를 자동 다운로드하지 않으며 `assets/`는 Git 제외 대상입니다.

Claude의 Clawd를 연상시키는 캔버스 캐릭터도 유지되어 있습니다. 직접 그린 코드와 별개로
브랜드 캐릭터로서의 외부 배포 조건은 확인이 남아 있습니다. 코드 라이선스가 브랜드 권리를 부여하지 않습니다.

**배포 방식:** 이미지 파일을 제외한 소스만 공개하고 사용자 PC의 기존 이미지를 읽습니다. 로컬 파일 읽기 기능이 별도의 자산 사용 허가를 부여하는 것은 아닙니다.
출처 표기만으로 권리가 확보되었다고 표시하거나, 이미지를 프로젝트 MIT 라이선스로 재허가하지 않습니다.

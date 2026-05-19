# 🌐 Streamlit Community Cloud 배포 가이드

집·휴대폰·아이패드 어디서든 URL 한 번이면 접속 가능하게 만듭니다.
바탕화면 아이콘, cmd 창, watchdog 모두 불필요해집니다.

**예상 시간**: 약 30~45분
**비용**: 무료 (GitHub + Streamlit Community Cloud 모두 무료 플랜)

---

## 0. 준비물

- GitHub 계정 ([github.com](https://github.com) 가입, 가입 시 무료)
- Anthropic API 키 (이미 있음 — `.env` 에 저장된 것)
- 본인이 정할 **앱 접근 비밀번호** (영어+숫자 12자 이상 권장)

---

## 1. GitHub 비공개 리포 만들기

1. [github.com](https://github.com) 로그인 → 우상단 **➕ → New repository**
2. 입력값:
   - **Repository name**: `alcofind-linkedin` (자유롭게)
   - **Description**: `ALCOFIND LinkedIn Composer` (자유)
   - **Visibility**: 🔒 **Private** 반드시 선택
   - 나머지 기본값 그대로 (README/.gitignore 체크 X)
3. **Create repository** 클릭

생성 직후 화면에 보이는 URL 복사해두세요 — 예: `https://github.com/김진호계정/alcofind-linkedin.git`

---

## 2. 로컬 코드를 GitHub에 푸시

PowerShell에서 한 번만 (이후엔 변경 있을 때만):

```powershell
cd "C:\Users\jhkim\Documents\Claude code\linkedin\app"

# Git 초기 설정 (한 번만)
git init
git config user.name "김진호"
git config user.email "본인이메일@example.com"

# 첫 커밋
git add .
git commit -m "Initial commit: ALCOFIND LinkedIn Composer"

# GitHub 리포 연결 (1단계에서 복사한 URL 사용)
git remote add origin https://github.com/김진호계정/alcofind-linkedin.git
git branch -M main
git push -u origin main
```

푸시 시 GitHub 로그인 창 또는 토큰 요구할 수 있음:
- 만약 비밀번호 인증 막혀있으면: [github.com/settings/tokens](https://github.com/settings/tokens) → **Generate new token (classic)** → `repo` 권한만 체크 → 생성된 토큰을 비밀번호 대신 입력

푸시 성공 후 GitHub 리포 페이지를 새로고침하면 `app.py`·`config.py` 등 파일이 보입니다.

> 🔍 **확인**: `.env`·`out/`·`history/`·`.venv/`는 .gitignore로 제외되어 **GitHub에 안 올라갑니다.** 키 노출 X.

---

## 3. Streamlit Community Cloud 가입 + 연결

1. [share.streamlit.io](https://share.streamlit.io) 접속 → **Continue with GitHub** (방금 만든 GitHub 계정으로 가입)
2. 가입 직후 첫 화면에서 **Create app** 또는 **New app** 클릭
3. 입력:
   - **Repository**: `김진호계정/alcofind-linkedin` 선택
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: 원하는 슬러그 (예: `alcofind-linkedin`) — 최종 URL은 `https://alcofind-linkedin.streamlit.app`
4. **⚙️ Advanced settings** 클릭 → **Python version**: 3.12 선택 (드롭다운)
5. 같은 Advanced settings 화면의 **Secrets** 칸에 아래 내용 그대로 붙여넣기 후 키만 본인 값으로:

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-본인키여기"
APP_PASSWORD = "본인이정한비밀번호"
```

6. **Deploy!** 클릭

---

## 4. 배포 진행 + 첫 접속

- 약 2~5분간 빌드 로그가 화면에 흐름 (`Installing requirements.txt...`)
- 완료되면 자동으로 앱 화면이 열림
- 🔒 비밀번호 입력 화면 등장 → 3-5단계의 `APP_PASSWORD` 입력 → 진입

이제 **`https://alcofind-linkedin.streamlit.app`** (또는 본인이 정한 URL)이 어디서든 접근 가능한 운영 URL입니다.

---

## 5. 자주 묻는 운영 질문

### Q1. 코드를 수정한 후 어떻게 반영?

로컬에서 코드 수정 → PowerShell:

```powershell
cd "C:\Users\jhkim\Documents\Claude code\linkedin\app"
git add .
git commit -m "변경 사항 설명"
git push
```

푸시 후 1~2분이면 Streamlit Cloud가 자동 감지하고 재배포합니다.

### Q2. 키가 만료되었거나 비밀번호 바꾸고 싶으면?

[share.streamlit.io](https://share.streamlit.io) → 본인 앱 → **⋯ → Settings → Secrets** 에서 값 수정 → Save. 1분 내 반영.

### Q3. 휴대폰에서도 잘 보이나?

Streamlit은 모바일 반응형이라 자동으로 잘 보이지만, 입력창은 PC에서 작업하시는 게 편합니다. 휴대폰은 빠른 확인 / 게시 직전 검토 용도.

### Q4. 다른 사람한테 URL 알려줘도 되나?

URL은 공개되어 있어도 비밀번호로 보호되므로 안전합니다. 다만 **비밀번호는 절대 채팅·이메일·문서에 평문으로 적지 마세요.** 직접 만나거나 1Password 같은 도구로 전달.

### Q5. 무료 플랜 제약은?

- 앱 한 개당 ~1GB RAM, 1 CPU
- 30분 비활성 시에도 Streamlit Community Cloud는 **잠들지 않음** (Hugging Face Spaces 등과 다름)
- 동시 접속자 1~2명까지 쾌적
- 본인 혼자 쓰는 용도엔 충분

### Q6. 로컬은 이제 필요 없나?

- **클라우드**: 평소 운영용 (포스트 작성·게시)
- **로컬**: 코드 수정·테스트용 (변경 후 git push로 클라우드 반영)
- 둘 다 같은 코드 베이스라 한쪽에서 만든 것이 다른 쪽에서도 동작

### Q7. 생성된 이미지·히스토리는 어디 저장?

클라우드 컨테이너의 임시 디스크에 저장됩니다. 컨테이너 재시작 시 (드물지만) 휘발될 수 있음. 영구 보관이 필요하면:
- 이미지는 게시 직후 PNG 다운로드해 PC에 보관
- 히스토리도 본인이 git push로 GitHub에 영구 저장 가능 (단, `out/`·`history/`는 .gitignore이므로 별도 처리 필요)

---

## 🚨 보안 체크리스트

배포 후 다음을 한 번 확인:

- [ ] GitHub 리포가 **Private**으로 설정되어 있는지 ([github.com/김진호계정/alcofind-linkedin/settings](https://github.com))
- [ ] GitHub 리포에 `.env` 파일이 **올라가지 않았는지** (리포 파일 목록에서 .env 검색)
- [ ] Streamlit Cloud 앱이 **본인만 보이는지** ([share.streamlit.io](https://share.streamlit.io)에서 본인 앱 확인)
- [ ] 비밀번호가 본인만 알고 있는지

문제 생기면: Streamlit Cloud 콘솔 → **Settings → Secrets** 즉시 변경, 또는 **Delete app**으로 앱 자체 삭제.

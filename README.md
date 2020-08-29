# 팀 크레센도 라라봇
팀 크레센도의 결제 시스템 [FORTE API](https://github.com/team-crescendo/laravel-forte-api)와
연동되는 디스코드 챗봇입니다. 다음과 같은 기능들을 제공합니다.

1. 팀 크레센도 이용자에게 일정량의 포인트를 제공하는 출석 체크 시스템.
2. (관리자 전용) 포르테 이용자의 정보를 열람하고 포인트를 지급할 수 있는 기능.

## 설치 및 실행

### 1. `.env` 파일 설정하기
`.env.example` 파일을 이용하여 적절한 설정 값을 입력해주세요.

### 2. Python 패키지 설치하기
라라봇은 Python 3.7.7 기준으로 개발되었으니 이 점 참고하시길 바랍니다.
`requirements.txt` 파일에 정의된 의존 패키지들을 설치해주세요.

### 3. 챗봇 실행하기

```sh
$ ./deploy.sh
appending output to nohup.out
```

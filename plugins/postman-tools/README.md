# postman-tools

Postman 컬렉션 관리를 자동화하는 skill 모음. **Postman REST API 직접 호출 방식** (MCP 서버 불필요).

## Skills

| Skill | 설명 |
|---|---|
| `postman-request` | request 생성/수정 (URL, params, body, docs) |
| `postman-docs-review` | request 설정과 docs를 코드와 대조 검증 |
| `postman-example` | request에 example(saved response) 생성 |

## 설정 (`.claude/plugins.json`)

```jsonc
{
  "postman-tools": {
    "workspaceId": "<workspace-uuid>",
    "workspaceName": "<workspace-name>",
    "backendStack": "Kotlin Spring Boot",
    "services": {
      "api": "{{API-HOST}}"
    },
    "collectionUid": "<owner>-<uuid>",
    "apiKeyFile": "~/.postman-api-key"
  }
}
```

> Jackson 네이밍 전략은 각 skill이 프로젝트의 `application.yml`/`application.properties`(또는 Java/Kotlin config)에서 `spring.jackson.property-naming-strategy`를 직접 찾아 결정한다. 설정이 없으면 Spring Boot 기본값(`LOWER_CAMEL_CASE`)으로 간주한다.

## 사전 준비

Postman API Key를 발급받아 로컬 파일에 저장:

```bash
# 1. https://go.postman.co/settings/me/api-keys 에서 API Key 발급 (PMAK-...)
# 2. 파일로 저장
echo "PMAK-your-key-here" > ~/.postman-api-key
chmod 600 ~/.postman-api-key
```

> API Key는 컬렉션 owner와 동일 계정의 키여야 한다 (다른 계정 키는 403).

## API 사용 엔드포인트

| 작업 | 엔드포인트 |
|---|---|
| 워크스페이스 목록 | `GET /workspaces` |
| 컬렉션 목록 | `GET /collections?workspace={id}` |
| 컬렉션 조회 | `GET /collections/{owner-uuid}` |
| 컬렉션 교체 | `PUT /collections/{owner-uuid}` |
| 예제(response) 생성 | `POST /collections/{id}/responses?request={requestId}` |

Base URL: `https://api.getpostman.com`  
Auth: `X-Api-Key: ${apiKey}`

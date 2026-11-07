# ADR 0001 — Fundação e execução local

Aceito para a Fase 0, em 06/11/2026.

- **Stack e Windows (D002):** Windows é o alvo inicial. React e TypeScript estrito com Vite mantêm a interface como aplicação web; FastAPI e Pydantic v2 mantêm validação e contratos na fronteira HTTP. Node 24 e Python 3.14 têm versões fixadas no CI. O npm instala as dependências em `Frontend/`; o ambiente virtual Python fica em `Backend/.venv/`. Cada aplicação tem seu próprio lockfile.
- **Contratos:** rotas de produto sob `/api/v1`. Os modelos Pydantic geram a descrição OpenAPI. Regras de negócio devem ficar no domínio; a camada de aplicação coordena casos de uso, e a infraestrutura implementa as portas.
- **SQLite:** persistência local por SQLAlchemy, com alterações de esquema por Alembic a partir de B003. SQLite reduz requisitos de instalação; concorrência de escrita e consistência de backup deverão ser testadas antes da distribuição.
- **SSE:** eventos de geração via HTTP e cancelamento por rota separada quando houver jobs reais. Uma conexão interrompida não confirma conclusão; o estado final virá da API e conteúdo provisório não será tratado como validado.
- **Execução e segurança:** ambos os servidores escutam em loopback; o proxy do frontend preserva a mesma origem. Sem telemetria do produto por padrão. Pesquisa externa exige consentimento por operação; provedores externos exigem autorização para transmissão. Não guardar segredos no Git nem no frontend.
- **Licenças (D003):** verificar licenças e avisos das dependências diretas e transitivas antes de adotar e ao atualizar. Preferir licenças permissivas e registrar obrigações de redistribuição. A licença do produto permanece em aberto até antes da distribuição.
- **Limites:** a matriz inicial cobre desenvolvimento Windows. O diagnóstico não certifica desempenho de modelos. Hardware de 6 GB, biblioteca de desenho, publicação e demais decisões futuras continuam sujeitos aos marcos correspondentes.

Na revisão inicial, os metadados do lockfile npm e dos pacotes Python instalados indicaram MIT, BSD, Apache-2.0, ISC, PSF-2.0 e MPL-2.0. A MPL-2.0 aparece em Lightning CSS, Certifi e Pathspec: registrar os avisos e revisar as obrigações relativas aos arquivos cobertos caso sejam redistribuídos. Esta triagem cobre as dependências atuais do ambiente de desenvolvimento; a auditoria dos artefatos distribuídos permanece em B025.

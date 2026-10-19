# Falhas (só acrescentar; ao fim, a menor correção vira linha no FALHAS.md do projeto)

| data | o que quebrou | tentativa | resultado | prompt \| infra |
|---|---|---|---|---|
| 2026-10-19 13:52 | Suíte inicial: 66 falhas por funcionalidades ausentes, incluindo README Deploy | Implementar base/inventário/tarifas e acrescentar seção sem remover conteúdo | Final 33 passed / 65 failed; funcionalidades restantes no state/plan, nenhum conflito identificado | infra (implementação incompleta) |
| 2026-10-19 13:56 | 38 testes ainda falham por áreas não implementadas (cadastros, páginas, Docker, iCal, integrações, LGPD/Raio-X) | Implementar conversa/ciclo e verificar regressão | 60 passed / 38 failed; 25 testes de conversa/ciclo passam; nenhum conflito teste/spec identificado | infra (implementação incompleta) |

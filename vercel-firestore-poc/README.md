# Protótipo comparativo — Firestore direto do navegador

Isto NÃO é o GEC. É uma amostra de uma única tela (Unidades) para comparar com
a versão real em Flask/SQL antes de decidir se vale migrar o sistema inteiro.

Esta versão fala **direto do navegador com o Firestore** — sem servidor, sem
chave secreta. A pasta `api/` (função serverless com Admin SDK) ficou como
alternativa caso você queira comparar as duas abordagens depois, mas a página
`index.html` hoje usa só o `firebase-config.js`.

## Antes de publicar

1. Preencha [firebase-config.js](firebase-config.js) com os dados do seu
   projeto (Firebase Console → Configurações do projeto → Geral → "Seus apps"
   → app Web). Esses valores não são secretos, podem ir pro GitHub sem
   problema.
2. Publique as regras de [firestore.rules](firestore.rules) no seu projeto:
   Firebase Console → Firestore Database → aba "Regras" → cole o conteúdo do
   arquivo → Publicar. **Sem isso, por padrão o Firestore recém-criado ou
   nega tudo ou libera tudo**, dependendo do modo escolhido ao criar — as
   regras daqui liberam leitura pra todo mundo e escrita só com os campos
   certos, sem permitir editar/apagar.
3. No Firestore, crie a collection `unidades` (pode deixar vazia, a página cria
   os documentos sozinha ao salvar o primeiro registro pelo formulário).

## Publicar na Vercel

Como não tem mais função serverless nem variável de ambiente secreta, o
deploy fica bem direto:
- **Pelo GitHub**: suba a pasta `vercel-firestore-poc` pro repositório e
  conecte na Vercel. Não precisa configurar nenhuma variável de ambiente.
- **Direto do computador**: `cd vercel-firestore-poc && vercel --prod`.

## O que isto NÃO mostra

- Telas com relacionamento (ex: Setor, que consulta Centro de Custo e
  Colaboradores juntos — no Firestore isso exige desnormalizar os dados ou
  fazer várias leituras separadas, sem JOIN).
- Login pelo sistema (aqui não tem autenticação — é só a tela de Unidades
  pública, protegida apenas pelas regras acima).
- Qualquer uma das outras ~66 tabelas do GEC.

# Protótipo comparativo — Firestore + Netlify

Isto NÃO é o GEC. É uma amostra de uma única tela (Unidades) reescrita para
Firestore + Netlify Functions, só para você comparar lado a lado com a versão
real em Flask/SQL antes de decidir se vale migrar o sistema inteiro.

## O que dá pra comparar aqui
- Como fica o código de uma tela simples (CRUD de uma tabela sem relacionamento)
  em Firestore vs. SQL.
- Como é o fluxo de deploy no Netlify.

## O que isto NÃO mostra
- Telas com relacionamento (ex: Setor, que teria que consultar Centro de Custo
  e Colaboradores juntos — em Firestore isso exige desnormalizar os dados ou
  fazer várias leituras separadas, sem JOIN).
- Login pelo sistema (aqui não tem autenticação nenhuma — é só a tela de
  Unidades pública, para simplificar a demonstração).
- Qualquer uma das outras ~66 tabelas do GEC.

## Como rodar
1. No Firebase Console, crie um projeto e ative o Firestore (modo produção).
2. Gere uma chave de serviço: Configurações do projeto → Contas de serviço →
   Gerar nova chave privada (baixa um .json).
3. No Netlify, crie um site apontando para esta pasta (`netlify-firestore-poc`)
   e configure a variável de ambiente `FIREBASE_SERVICE_ACCOUNT` colando o
   conteúdo inteiro do .json (numa linha só).
4. Deploy. A página fica em `/` e a função em `/.netlify/functions/unidades`.

## Comparação de código: a mesma operação nos dois mundos

**Flask + SQL (GEC hoje)** — `cadastros.py`:
```python
lista = db.execute("SELECT * FROM unidades ORDER BY nome").fetchall()
db.execute("INSERT INTO unidades (nome, endereco) VALUES (?, ?)", (nome, endereco))
```

**Firestore + Netlify** — `netlify/functions/unidades.js`:
```js
const snap = await db.collection("unidades").orderBy("nome").get();
const unidades = snap.docs.map(doc => ({ id: doc.id, ...doc.data() }));

await db.collection("unidades").add({ nome, endereco, ativo: true });
```

Para uma tabela isolada como Unidades, a diferença é pequena. O custo real
aparece nas telas com JOIN — que são a maioria do GEC.

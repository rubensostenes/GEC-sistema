// Função Netlify equivalente à rota Flask cadastros.unidades / cadastros.nova_unidade.
// GET  -> lista as unidades (equivalente a "SELECT * FROM unidades ORDER BY nome")
// POST -> cria uma unidade (equivalente ao INSERT INTO unidades)
//
// Credencial: defina a variável de ambiente FIREBASE_SERVICE_ACCOUNT no Netlify
// com o conteúdo JSON da chave de serviço (Configurações do projeto > Contas de
// serviço > Gerar nova chave privada), colado como uma linha só.

const admin = require("firebase-admin");

if (!admin.apps.length) {
  const credencial = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
  admin.initializeApp({ credential: admin.credential.cert(credencial) });
}

const db = admin.firestore();

exports.handler = async (event) => {
  if (event.httpMethod === "GET") {
    const snap = await db.collection("unidades").orderBy("nome").get();
    const unidades = snap.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
    return { statusCode: 200, body: JSON.stringify(unidades) };
  }

  if (event.httpMethod === "POST") {
    const dados = JSON.parse(event.body || "{}");
    const nome = (dados.nome || "").trim();
    if (!nome) {
      return { statusCode: 400, body: JSON.stringify({ erro: "Nome é obrigatório." }) };
    }
    const doc = await db.collection("unidades").add({
      nome,
      endereco: (dados.endereco || "").trim(),
      ativo: true,
      criado_em: admin.firestore.FieldValue.serverTimestamp(),
    });
    return { statusCode: 201, body: JSON.stringify({ id: doc.id }) };
  }

  return { statusCode: 405, body: "Método não suportado" };
};

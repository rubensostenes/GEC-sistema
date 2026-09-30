// Equivalente Vercel da função Netlify netlify-firestore-poc/netlify/functions/unidades.js
// Mesma lógica (Firebase Admin SDK / Firestore) — só a assinatura do handler muda,
// porque a Vercel usa (req, res) no lugar de (event) => {statusCode, body}.
//
// Credencial: defina a variável de ambiente FIREBASE_SERVICE_ACCOUNT no painel da
// Vercel (Project Settings > Environment Variables) com o JSON da chave de serviço
// colado como uma linha só.

const admin = require("firebase-admin");

if (!admin.apps.length) {
  const credencial = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
  admin.initializeApp({ credential: admin.credential.cert(credencial) });
}

const db = admin.firestore();

module.exports = async (req, res) => {
  if (req.method === "GET") {
    const snap = await db.collection("unidades").orderBy("nome").get();
    const unidades = snap.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
    return res.status(200).json(unidades);
  }

  if (req.method === "POST") {
    const dados = typeof req.body === "string" ? JSON.parse(req.body) : req.body || {};
    const nome = (dados.nome || "").trim();
    if (!nome) {
      return res.status(400).json({ erro: "Nome é obrigatório." });
    }
    const doc = await db.collection("unidades").add({
      nome,
      endereco: (dados.endereco || "").trim(),
      ativo: true,
      criado_em: admin.firestore.FieldValue.serverTimestamp(),
    });
    return res.status(201).json({ id: doc.id });
  }

  return res.status(405).send("Método não suportado");
};

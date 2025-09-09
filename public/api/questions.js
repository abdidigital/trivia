// Data pertanyaan trivia
const questions = {
  sejarah: [
    {
      question: 'Siapa presiden pertama Indonesia?',
      answers: ['Soekarno', 'Soeharto', 'BJ Habibie'],
      correct: 'Soekarno',
    },
    {
      question: 'Kapan Indonesia merdeka?',
      answers: ['17 Agustus 1945', '28 Oktober 1928', '11 Maret 1966'],
      correct: '17 Agustus 1945',
    },
    // Tambahkan lebih banyak pertanyaan sejarah...
  ],
  sains: [
    {
      question: 'Apa rumus kimia air?',
      answers: ['H2O', 'CO2', 'O2'],
      correct: 'H2O',
    },
    {
      question: 'Apa planet terdekat dari Matahari?',
      answers: ['Merkurius', 'Venus', 'Bumi'],
      correct: 'Merkurius',
    },
    // Tambahkan lebih banyak pertanyaan sains...
  ],
};

module.exports = (req, res) => {
  const category = req.query.category;
  if (questions[category]) {
    res.status(200).json(questions[category]);
  } else {
    res.status(404).send('Kategori tidak ditemukan.');
  }
};

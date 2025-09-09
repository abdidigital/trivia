// public/script.js
let currentQuestions = [];
let currentQuestionIndex = 0;
let score = 0;

async function startGame(category) {
  Telegram.WebApp.ready();
  document.getElementById('category-selection').style.display = 'none';
  document.getElementById('quiz-container').style.display = 'block';

  try {
    const response = await fetch(`/api/questions?category=${category}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    currentQuestions = await response.json();
    currentQuestionIndex = 0;
    score = 0;
    document.getElementById('score').innerText = score;

    // Periksa jika tidak ada pertanyaan yang dimuat
    if (currentQuestions.length > 0) {
      showQuestion();
    } else {
      alert("Tidak ada pertanyaan untuk kategori ini.");
      restartGame();
    }
  } catch (error) {
    console.error("Gagal memuat pertanyaan:", error);
    alert("Gagal memuat kuis. Coba lagi nanti.");
    restartGame();
  }
}

function showQuestion() {
  if (currentQuestionIndex < currentQuestions.length) {
    const q = currentQuestions[currentQuestionIndex];
    document.getElementById('question').innerText = q.question;
    const answersDiv = document.getElementById('answers');
    answersDiv.innerHTML = '';
    
    q.answers.forEach((answer) => {
      const button = document.createElement('button');
      button.innerText = answer;
      button.onclick = () => checkAnswer(answer, q.correct);
      answersDiv.appendChild(button);
    });
  } else {
    showResult();
  }
}

function checkAnswer(selected, correct) {
  if (selected === correct) {
    score++;
  }
  document.getElementById('score').innerText = score;

  currentQuestionIndex++;
  showQuestion();
}

function showResult() {
  document.getElementById('quiz-container').style.display = 'none';
  document.getElementById('result-container').style.display = 'block';
  document.getElementById('final-score').innerText = `${score} / ${currentQuestions.length}`;
}

function restartGame() {
  document.getElementById('result-container').style.display = 'none';
  document.getElementById('category-selection').style.display = 'block';
}

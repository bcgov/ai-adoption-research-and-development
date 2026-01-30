// Simple demo: upload a file, send to backend, show result
const form = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');

const resultDiv = document.getElementById('result');
const previewDiv = document.getElementById('preview');

fileInput.addEventListener('change', () => {
  previewDiv.innerHTML = '';
  const file = fileInput.files[0];
  if (!file) return;
  if (file.type.startsWith('image/')) {
    const img = document.createElement('img');
    img.style.maxWidth = '100%';
    img.style.height = 'auto';
    img.style.display = 'block';
    img.src = URL.createObjectURL(file);
    previewDiv.appendChild(img);
  } else if (file.type === 'application/pdf') {
    const pdfIcon = document.createElement('div');
    pdfIcon.textContent = 'PDF selected: ' + file.name;
    pdfIcon.style.fontWeight = 'bold';
    previewDiv.appendChild(pdfIcon);
  } else {
    const info = document.createElement('div');
    info.textContent = 'Selected: ' + file.name;
    previewDiv.appendChild(info);
  }
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  resultDiv.style.display = 'block';
  resultDiv.textContent = 'Uploading and classifying...';
  resultDiv.classList.add('loading');

  const file = fileInput.files[0];
  if (!file) {
    resultDiv.textContent = 'No file selected.';
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    const resp = await fetch('/demo/classify', {
      method: 'POST',
      body: formData
    });
    if (!resp.ok) {
      resultDiv.textContent = 'Error: ' + resp.status + ' ' + resp.statusText;
      resultDiv.classList.remove('loading');
      return;
    }
    const data = await resp.json();
    resultDiv.classList.remove('loading');
    resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
  } catch (err) {
    resultDiv.textContent = 'Error: ' + err;
    resultDiv.classList.remove('loading');
  }
});

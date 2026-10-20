'use strict';
const dialog = document.getElementById('figure-dialog');
document.querySelectorAll('a.zoom').forEach(link => {
  link.addEventListener('click', event => {
    if (typeof dialog.showModal !== 'function') return;
    event.preventDefault();
    const source = link.querySelector('img');
    const enlarged = document.getElementById('enlarged-figure');
    enlarged.src = link.href;
    enlarged.alt = source.alt;
    document.getElementById('enlarged-caption').textContent = link.closest('figure').querySelector('figcaption').textContent;
    dialog.showModal();
  });
});
document.getElementById('close-figure').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if(event.target === dialog) dialog.close(); });
document.getElementById('copy-citation').addEventListener('click', async () => {
  const status = document.getElementById('copy-status');
  try {
    await navigator.clipboard.writeText(document.getElementById('bibtex').textContent);
    status.textContent = 'Copied';
  } catch {
    const range = document.createRange();
    range.selectNodeContents(document.getElementById('bibtex'));
    const selection = window.getSelection();
    selection.removeAllRanges(); selection.addRange(range);
    status.textContent = 'Select Copy, or download the BibTeX file.';
  }
});

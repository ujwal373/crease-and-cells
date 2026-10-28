export function renderGrid(
  tableEl: HTMLTableElement,
  sheet: (string | number | null)[][],
): void {
  tableEl.innerHTML = '';
  const headers = sheet[0];
  if (!headers) return;

  const thead = tableEl.createTHead();
  const headerRow = thead.insertRow();
  const thNum = document.createElement('th');
  thNum.className = 'row-num';
  headerRow.appendChild(thNum);
  for (const cell of headers) {
    const th = document.createElement('th');
    th.textContent = cell === null ? '' : String(cell);
    headerRow.appendChild(th);
  }

  const tbody = tableEl.createTBody();
  const dataRows = sheet.slice(1);
  dataRows.forEach((row, idx) => {
    const tr = tbody.insertRow();
    const tdNum = tr.insertCell();
    tdNum.className = 'row-num';
    tdNum.textContent = String(idx + 2);
    for (const cell of row) {
      const td = tr.insertCell();
      td.textContent = cell === null ? '' : String(cell);
      if (typeof cell === 'number') td.classList.add('cell-num');
    }
  });
}

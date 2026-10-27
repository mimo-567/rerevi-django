'use strict';
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-visual-editor]').forEach(wrapper => {
    const input = wrapper.querySelector('textarea');
    const surface = wrapper.querySelector('.visual-surface');
    surface.innerHTML = input.value; // Content is sanitised on save and before rendering.
    input.hidden = true;
    let selectionRange = null;
    const remember = () => {
      const selection = window.getSelection();
      if (selection.rangeCount && surface.contains(selection.anchorNode) && surface.contains(selection.focusNode)) selectionRange = selection.getRangeAt(0).cloneRange();
    };
    const restore = () => {
      surface.focus();
      if (selectionRange && surface.contains(selectionRange.commonAncestorContainer)) {
        const selection = window.getSelection();
        selection.removeAllRanges(); selection.addRange(selectionRange);
      }
    };
    const sync = () => { input.value = surface.innerHTML; };
    surface.addEventListener('input', sync);
    surface.addEventListener('keyup', remember);
    surface.addEventListener('mouseup', remember);
    surface.addEventListener('blur', remember);
    wrapper.querySelectorAll('.visual-toolbar button').forEach(button => {
      button.addEventListener('mousedown', event => event.preventDefault());
      button.addEventListener('click', () => {
        restore();
        if (button.hasAttribute('data-link')) {
          const url = window.prompt('Link address (https://…, mailto:…, /page/ or #section)');
          if (!url) return;
          if (!/^(https?:\/\/|mailto:|\/(?!\/)|#)/i.test(url.trim()) || /[\u0000-\u0020\\]/.test(url.trim())) {
            window.alert('Enter a valid website address, email link or local page path.'); return;
          }
          restore(); document.execCommand('createLink', false, url.trim());
        } else if (button.dataset.block) document.execCommand('formatBlock', false, button.dataset.block);
        else document.execCommand(button.dataset.command, false, null);
        sync(); remember();
      });
    });
    // Plain-text paste avoids executing embedded markup inside the editor.
    surface.addEventListener('paste', event => {
      event.preventDefault();
      document.execCommand('insertText', false, event.clipboardData.getData('text/plain'));
      sync();
    });
    surface.addEventListener('drop', event => event.preventDefault());
    input.form.addEventListener('submit', sync);
  });
});

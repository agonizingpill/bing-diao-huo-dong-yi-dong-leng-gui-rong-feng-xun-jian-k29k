import {request} from './api.js';
import {actionForm} from './controls.js';
import {el} from './dom.js';
import {dataView, status, titleBlock} from './widgets.js';

export function workspace(root, role, page) {
  const panel = el('section', {class:'ledger', 'aria-label':page.caption});
  const extras = (page.extra || []).map(extra => ({...extra,
    node:el('section', {class:'ledger', 'aria-label':extra.caption})}));
  const load = async (target, config) => {
    const rows = await request(config.path);
    target.replaceChildren(el('h2',{},config.caption),dataView(rows, config.columns, config.view));
  };
  const refresh = async () => {
    try {
      await load(panel, page);
      for (const extra of extras) await load(extra.node, extra);
    } catch (error) { panel.replaceChildren(status(error.message,'error')); }
  };
  const actions = page.actions.filter(x => x.roles.includes(role));
  root.replaceChildren(titleBlock(page.module, page.title, page.detail),
    el('div',{class:'work '+page.layout},panel,
      actions.length ? el('section',{class:'actions'},actions.map(x => actionForm(x, refresh))) : null),
    ...extras.map(extra => extra.node));
  return refresh();
}

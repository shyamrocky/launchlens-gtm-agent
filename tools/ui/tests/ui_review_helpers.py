"""Interactions for the single-card UI, using only authored offline/mock runs."""
def finish_stack(app):
    for _ in range(40):
        buttons=[b for b in app.button if (b.key or '').startswith('keep-phrase-')]
        if not buttons:break
        buttons[0].click().run()
        assert not app.exception
    assert any(b.key=='create-next-version' for b in app.button)
    return app

def show_card(app,group):
    from launchlens.review_decisions import grouped_findings
    s=app.session_state['offline_run'].snapshot()
    groups=[g for g in grouped_findings(s) if g['needs_attention']]
    app.session_state['run-review-position-'+s['run_id']]=next(i for i,g in enumerate(groups) if g['id']==group['id'])
    app.run();return app

"""Interactions for the single-card UI, using only authored offline/mock runs."""
def finish_stack(app,request_changes=False):
    for _ in range(40):
        buttons=[b for b in app.button if (b.key or '').startswith('changes-' if request_changes else 'keep-phrase-')]
        if not buttons:break
        buttons[0].click().run()
        assert not app.exception
    assert any(b.key=='create-next-version' for b in app.button)
    return app

def show_card(app,group):
    from launchlens.review_decisions import grouped_findings
    s=app.session_state['offline_run'].snapshot()
    from launchlens.package_presentation import must_decide
    groups=[g for g in grouped_findings(s) if must_decide(g)]
    app.session_state['run-review-position-'+s['run_id']]=next((i for i,g in enumerate(groups) if g['id']==group['id']),len(groups))
    app.run();return app


def finish_pending(app,run=None):
    """Keep only undecided cards, preserving choices made earlier in the stack."""
    from launchlens.review_decisions import grouped_findings,effective_choice
    from launchlens.package_presentation import must_decide
    run=run or app.session_state['offline_run'];state=run.snapshot()
    groups=[g for g in grouped_findings(state) if must_decide(g)]
    for i,group in enumerate(groups):
        book=app.session_state['run-review-decisions-'+state['run_id']]
        if all(effective_choice(book,group,o) for o in group['occurrences'] if o['needs_attention']):continue
        app.session_state['run-review-position-'+state['run_id']]=i;app.run()
        app.button(key='keep-'+group['id']).click().run()
        assert not app.exception
    app.session_state['run-review-position-'+state['run_id']]=len(groups);app.run()
    return app

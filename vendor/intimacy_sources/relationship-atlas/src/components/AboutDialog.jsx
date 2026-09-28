import { useEffect, useRef } from 'react'
import { meta } from '../catalog'
import discoveryTerms from '../data/discovery-terms.json'
import { CloseIcon } from './Icons'

export function AboutDialog({ open, onClose }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog ref={dialogRef} className="about-dialog" onClose={onClose}>
      <div className="dialog-heading">
        <div><h2>About this data</h2><p>Captured {meta.captured}</p></div>
        <button className="icon-button" type="button" aria-label="Close" onClick={onClose}><CloseIcon /></button>
      </div>
      <div className="coverage-list">
        <div><strong>{meta.relationshipCount.toLocaleString()}</strong><span>relationship terms</span></div>
        <div><strong>{meta.roleCount.toLocaleString()}</strong><span>unique role labels</span></div>
        <div><strong>{meta.relationshipMenuCount.toLocaleString()}</strong><span>Add Relationship choices</span></div>
        <div><strong>{meta.dsMenuCount.toLocaleString()}</strong><span>Add D/s choices</span></div>
      </div>
      <section>
        <h3>Current coverage</h3>
        <p>By default, Relationships shows the {meta.relationshipMenuCount} choices captured from the authenticated Add Relationship menu, and D/s &amp; Profile Roles shows the {meta.dsMenuCount} choices captured from the authenticated Add D/s menu. Turn on Full reference library to browse all {meta.relationshipCount} relationship terms or {meta.roleCount} role labels. Reference-only terms are identified and may not be selectable on a FetLife profile.</p>
      </section>
      <section>
        <h3>Definitions</h3>
        <p>Definition text is identified per entry. “Verbatim FetLife excerpt” preserves a short passage from the cited source. “Adapted summary” is rewritten reference text and is not FetLife’s exact wording. “No platform definition captured” means no definition was retained from the captured source.</p>
      </section>
      <section>
        <h3>Source, attribution, and license</h3>
        <p>FetLife’s Kinktionary is the attributed source for Kinktionary labels and excerpts. This independent atlas uses that material for noncommercial educational reference under the <a href="https://fetlife.com/kinktionary/license-zcfzz" target="_blank" rel="noreferrer">Kinktionary license</a>; adaptations are identified. Commercial use requires FetLife’s written permission. FetLife does not endorse this atlas.</p>
      </section>
      <section>
        <h3>Partner labels</h3>
        <p>A two-way pair appears only when both catalog labels point back to each other. When language depends on identity, context, or preference, the partner chooses their own label. Top/bottom activity and Dominant/submissive authority remain separate.</p>
      </section>
      <section>
        <h3>Search language</h3>
        <p>The global finder searches both catalogs and recognizes sourced community shorthand. Discovery terms were reviewed {discoveryTerms.captured}; they help locate existing labels but never become platform entries or definitions.</p>
      </section>
      <section>
        <h3>Privacy and consent</h3>
        <p>My Pairing stays in this browser’s local storage. No profile usernames are included in the published data. Labels are vocabulary—not consent, compatibility, or an agreement.</p>
      </section>
      <button className="primary-button dialog-close" type="button" onClick={onClose}>Done</button>
    </dialog>
  )
}

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__grid">
        <div>
          <div className="site-footer__brand">Uztelecom</div>
          <p className="site-footer__text">
            Milliy telekommunikatsiya operatorining rasmiy ulanish portali.
          </p>
          <a href="#about" className="site-footer__about-link">Biz haqimizda</a>
        </div>
        <div>
          <div className="site-footer__title">Aloqa</div>
          <p className="site-footer__text">Toshkent sh., Navoiy ko&apos;chasi, 9-uy</p>
          <a href="tel:+998712026060" className="site-footer__link">+998 71 202 60 60</a>
        </div>
        <div id="about">
          <div className="site-footer__title">Biz haqimizda</div>
          <p className="site-footer__text">
            Uztelecom — O&apos;zbekistonning eng yirik telekommunikatsiya operatori.
            Uy interneti, mobil aloqa va 24/7 qo&apos;llab-quvvatlash xizmatlarini taqdim etamiz.
          </p>
        </div>
      </div>
      <div className="site-footer__bottom">
        &copy; 2008–2026 Uztelecom. Barcha huquqlar himoyalangan.
      </div>
    </footer>
  );
}

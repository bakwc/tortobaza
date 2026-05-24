import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export default function TermsContentKa({ updatedLine }: { updatedLine: string }) {
  return (
    <>
      <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">წესები და პირობები</h1>
      <p className="mt-6 text-sm text-[var(--ink)]/70">{updatedLine}</p>
      <div className="mt-8 space-y-6 text-base leading-relaxed md:text-lg">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">მომმსახურების მხარე</h2>
          <p>
            საიტსა და ონლაინ შეკვეთას უზრუნველყოფს{" "}
            <span className="font-semibold">{SITE_INFO.legalName}</span> (ID {SITE_INFO.legalId}),
            სავაჭრო სახელით {SITE_INFO.brand}. მისამართი: {SITE_INFO.address.line1},{" "}
            {SITE_INFO.address.city}, {SITE_INFO.address.country}.{" "}
            <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
              {SITE_INFO.email}
            </Link>
            ,{" "}
            <Link href={SITE_INFO.phoneHref} className="underline underline-offset-2">
              {SITE_INFO.phone}
            </Link>
            .
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">შეკვეთები და ფასები</h2>
          <p>
            შეკვეთის გაგზავნით თქვენ სთავაზობთ კალათაში არსებული პოზიციების ყიდვას იმ ფასებში,
            რასაც ხედავთ checkout-ში. ფასები {SITE_INFO.currency}-შია. დადასტურება საიტზე
            ნაჩვენები პროცესის შესაბამისად ხდება.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">გადახდა</h2>
          <p>
            ბარათით გადახდას ამუშავებს ბანკი ან უფლებამოსილი პარტნირი. თქვენ აძლევთ უფლებას ნაჩვენები
            თანხის ჩამოჭრას არჩეული მეთოდით, შესაბამისად გადასახადით, თუ ეს მითითებულია.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Pickup და მიწოდება</h2>
          <p>
            შესრულების რეჟიმები და დროის სლოტები არის განმარტებული გვერდზე{" "}
            <Link href="/delivery-and-refunds" className="underline underline-offset-2">
              მიწოდება და თანხის დასაბრუნებლობა
            </Link>
            .
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">პასუხისმგებლობის შეზღუდვა</h2>
          <p>
            კანონით დაშვებულ ფარგლებში ჩვენ არ ვიღებთ პასუხისმგებლობას არაპირდაპირ ან შედეგობრივ
            ზიანისთვის. ამ წესებში მითითებული არაფერი არ ამორიცხავს იმ პასუხისმგებლობას, რომელიც
            მოქმედი მომხმარებელთა კანონმდებლობით მაინც ძალაშია.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">კანონმდებლობა</h2>
          <p>
            ამ წესებზე ვრცელდება საქართველოს კანონმდებლობა. ქალაქ {SITE_INFO.address.city}-ის
            სასამართლოებს აქვთ არაექსკლუზიური იურისდიქცია.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">კონფიდენციალურობა</h2>
          <p>
            იხილეთ{" "}
            <Link href="/privacy" className="underline underline-offset-2">
              კონფიდენციალურობის პოლიტიკა
            </Link>
            .
          </p>
        </section>
      </div>
    </>
  );
}

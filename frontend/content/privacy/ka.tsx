import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export default function PrivacyContentKa({ updatedLine }: { updatedLine: string }) {
  return (
    <>
      <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">კონფიდენციალურობის პოლიტიკა</h1>
      <p className="mt-6 text-sm text-[var(--ink)]/70">{updatedLine}</p>
      <div className="mt-8 space-y-6 text-base leading-relaxed md:text-lg">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">ვინ ვართ ჩვენ</h2>
          <p>
            {SITE_INFO.brand} ემსახურება <span className="font-semibold">{SITE_INFO.legalName}</span>{" "}
            (ID {SITE_INFO.legalId}), მისამართი {SITE_INFO.address.line1}, {SITE_INFO.address.city},{" "}
            {SITE_INFO.address.country}. კონტაქტი:{" "}
            <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
              {SITE_INFO.email}
            </Link>
            .
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">რა მონაცემებს ვაგროვებთ</h2>
          <p>
            შეკვეთისას ვაგროვებთ სახელს, ტელეფონს, ელფოსტას, მიწოდების ან pickup-ის დეტალებს, შეკვეთის
            შიგთავსს, გადახდასთან დაკავშირებულ მითითებებს ბანკის ან გადახდის პროვაიდერის მხრიდან და
            თქვენს კომენტარს შეკვეთაზე.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">რატომ ვიყენებთ</h2>
          <p>
            ინფორმაციას ვიყენებთ შეკვეთის დასადასტურებლად და შესასრულებლად, დროსა და შეკრებასთან
            კომუნიკაციისთვის, ბარათით გადახდის დასამუშავებლად კანონმდებლობის შესაბამისად და სერვისის
            გასაუმჯობესებლად.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">გაზიარება</h2>
          <p>
            გავაზიარებთ მონაცემებს პარტნიორებთან მხოლოდ საჭირო რაოდენობით — გადახდები, მასპინძლობა ან IT,
            მიწოდება თუ აირჩიეთ delivery. არ ვაყიდით პირად მონაცემებს.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">შენახვის პერიოდი</h2>
          <p>
            შეკვეთასა და გადახდასთან დაკავშირებულ ჩანაწერს ვინახავთ იმხელა ხანს, რამდენიც აუცილებელია
            ბუღალტრიისა და სასამართლო რისკისთვის, შემდეგ წავშლით ან ანონიმიზაციას გავუკეთებთ.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">თქვენი უფლებები</h2>
          <p>
            კანონმდებლობის შესაბამისად შეიძლება გქონდეთ წვდომა, გასასწორებლად და წასაშლელად განაცხადის
            უფლება. გამოგვიგზავნეთ შეტყობინება აქ:{" "}
            <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
              {SITE_INFO.email}
            </Link>
            .
          </p>
        </section>
      </div>
    </>
  );
}

import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export default function DeliveryContentKa({ updatedLine }: { updatedLine: string }) {
  return (
    <>
      <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">
        მიწოდება, დაბრუნება, გაუქმება და გადახდის დაბრუნება
      </h1>
      <p className="mt-6 text-sm text-[var(--ink)]/70">{updatedLine}</p>
      <div className="mt-8 space-y-8 text-base leading-relaxed md:text-lg">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">მიწოდება</h2>
          <p>
            ვახორციელებთ მიწოდებას {SITE_INFO.address.city}-სა და მის მახლობელ ზონებში, checkout-ისას
            როგორცაა შეთავაზებული. მიწოდების დრო არის თქვენ მიერ არჩეული დროის სლოტი; თუ ვერ
            დავასრულებთ, დაგიკავშირდებით თქვენ მიერ მითითებული კონტაქტებით. მიწოდების ღირებულება, თუ
            არსებობს, ჩანს გადახდამდე.
          </p>
          <p>
            რისკი გადადის თქვენზე, როცა შეკვეთა გადაეცემა თქვენ ან თქვენ მიერ მითითებულ მიმღებს
            მისამართზე ან pickup წერტილზე.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Pickup</h2>
          <p>
            Pickup-ისას, თუ მოგცემთ, მოიტანეთ შეკვეთის ნომერი. სამუშაო საათები და მისამართი — ჩვენს{" "}
            <Link href="/contacts" className="underline underline-offset-2">
              კონტაქტების
            </Link>{" "}
            გვერდზე.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">გაუქმება</h2>
          <p>
            შეკვეთის უფასოდ გაუქმება შესაძლებელია, თუ ჯერ არ დაგვიწყებია მისი წარმოება. დაგვიკავშირდით
            რაც შეიძლება სწრაფად{" "}
            <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
              {SITE_INFO.email}
            </Link>{" "}
            ან{" "}
            <Link
              href={SITE_INFO.whatsappHref}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              WhatsApp
            </Link>{" "}
            თქვენი შეკვეთის ნომრით. თუ წარმოება დაწყებულია, გაუქმება შეიძლება სრულად შეუძლებელი
            იყოს; დაგიდასტურებთ ხელმისაწვდომ ვარიანტებს.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">დაბრუნება</h2>
          <p>
            ტორტები და დესერტები სწრაფფორტიანია და ინდივიურად მზადდება. გადაცემის შემდეგ „გადაწყვეტილების
            შეცვლის“ გამო დაბრუნების უფლება არ გაქვთ. თუ ხარისხის ნაკლი ან ჩვენს მხრიდან ცხადი შეცდომაა,
            შეატყობინეთ გადაცემისას ან ორი საათის განმავლობაში, სასარგებლო შემთხვევაში ფოტოსთან;
            განვალაგებთ შესაბამის გამოსწორებას.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">გადახდის დაბრუნება</h2>
          <p>
            ბარათით გადახდის დამტკიცებული დაბრუნება ორიგინალ ბარათზე ხდება დამტკიცებიდან თოთხმეტი სამუშაო
            დღის განმავლობაში, თქვენი ბანკის მიხედვით. სხვა გზით გადახდისას, სადაც შესაძლებელია, იმავე
            მეთოდით ვაბრუნებთ.
          </p>
          <p>
            გადაცემის შემდეგ დამტკიცებული, სრულყოფილი, სწრაფფორტიანი შეკვეთისთვის დაბრუნება არ ითვლება,
            გარდა იმ შემთხვევებისა, როცა კანონი ამას მოითხოვს.
          </p>
        </section>
      </div>
    </>
  );
}

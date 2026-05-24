import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export default function DeliveryContentRu({ updatedLine }: { updatedLine: string }) {
  return (
    <>
      <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">
        Доставка, возвраты, отмена и возмещение
      </h1>
      <p className="mt-6 text-sm text-[var(--ink)]/70">{updatedLine}</p>
      <div className="mt-8 space-y-8 text-base leading-relaxed md:text-lg">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Доставка</h2>
          <p>
            Мы доставляем по {SITE_INFO.address.city} и прилегающим зонам, как предложено при оформлении.
            Доставка в выбранный слот времени; если не успеваем, связываемся по вашим контактам. Сбор за
            доставку показывается до оплаты, если есть.
          </p>
          <p>
            Риск переходит к вам в момент передачи заказа вам или вашему представителю по адресу или в
            пункте самовывоза.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Самовывоз</h2>
          <p>
            При самовывозе принесите номер заказа, если мы его сообщили. Часы работы и адрес на странице{" "}
            <Link href="/contacts" className="underline underline-offset-2">
              Контакты
            </Link>
            .
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Отмена</h2>
          <p>
            Бесплатная отмена возможна до начала производства по заказу. Напишите как можно быстрее на{" "}
            <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
              {SITE_INFO.email}
            </Link>
            или в{" "}
            <Link
              href={SITE_INFO.whatsappHref}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              WhatsApp
            </Link>{" "}
            с номером заказа. Если производство начато, мы предложим доступные варианты компенсации.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Возвраты</h2>
          <p>
            Изделия скоропортящиеся и готовятся индивидуально — нет возврата просто если передумали после
            передачи. При явном браке сообщите при выдаче или в течение двух часов с фото; предложим
            способ исправления.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Возврат денег</h2>
          <p>
            Одобренные возмещения по карте отправляются на ту же карту в течение четырнадцати рабочих дней
            после согласования, срок может зависеть от банка. При других способах оплаты стараемся
            использовать тот же канал.
          </p>
          <p>
            После принятия небракованного скоропортящегося продукта возврат не полагается, кроме случаев,
            когда это требует закон.
          </p>
        </section>
      </div>
    </>
  );
}

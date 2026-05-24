import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export default function PrivacyContentRu({ updatedLine }: { updatedLine: string }) {
  return (
    <>
      <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">
        Политика конфиденциальности
      </h1>
      <p className="mt-6 text-sm text-[var(--ink)]/70">{updatedLine}</p>
      <div className="mt-8 space-y-6 text-base leading-relaxed md:text-lg">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Кто мы</h2>
          <p>
            Сайт {SITE_INFO.brand} управляется{" "}
            <span className="font-semibold">{SITE_INFO.legalName}</span> (ID {SITE_INFO.legalId}),{" "}
            {SITE_INFO.address.line1}, {SITE_INFO.address.city}, {SITE_INFO.address.country}. Контакт:{" "}
            <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
              {SITE_INFO.email}
            </Link>
            .
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Какие данные мы собираем</h2>
          <p>
            При оформлении заказа мы обычно собираем имя, номер телефона, адрес электронной почты,
            данные для доставки или самовывоза, состав заказа, платёжные реквизиты и пометки банка
            или платёжного оператора, а также текст комментария к заказу.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Зачем мы их используем</h2>
          <p>
            Мы используем информацию для подтверждения и выполнения заказа, связи по срокам и
            проблемам, проведения оплаты через банк или платёжного партнёра, соблюдения требований
            законодательства и улучшения сервиса.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Передача третьим лицам</h2>
          <p>
            Мы делимся данными с провайдерами строго по необходимости: обработка платежей, хостинг и
            IT, курьеры при доставке. Мы не продаём ваши персональные данные.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Хранение</h2>
          <p>
            Мы храним записи заказов и платежей столько времени, сколько требуется для учёта,
            налогообложения и спорных ситуаций, затем удаляем или обезличиваем данные.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Ваши права</h2>
          <p>
            По применимому законодательству вы можете иметь право на доступ, исправление, удаление или
            ограничение обработки. Напишите нам на{" "}
            <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
              {SITE_INFO.email}
            </Link>{" "}
            — мы ответим в разумный срок.
          </p>
        </section>
      </div>
    </>
  );
}

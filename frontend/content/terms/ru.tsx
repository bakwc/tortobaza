import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export default function TermsContentRu({ updatedLine }: { updatedLine: string }) {
  return (
    <>
      <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">Условия обслуживания</h1>
      <p className="mt-6 text-sm text-[var(--ink)]/70">{updatedLine}</p>
      <div className="mt-8 space-y-6 text-base leading-relaxed md:text-lg">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Исполнитель</h2>
          <p>
            Сайт и онлайн-заказ предоставляются{" "}
            <span className="font-semibold">{SITE_INFO.legalName}</span> (ID {SITE_INFO.legalId}), под
            брендом {SITE_INFO.brand}. Адрес: {SITE_INFO.address.line1}, {SITE_INFO.address.city},{" "}
            {SITE_INFO.address.country}.{" "}
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
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Заказы и цены</h2>
          <p>
            Оформляя заказ, вы предлагаете купить товары из корзины по ценам, указанным при оплате. Все
            цены в {SITE_INFO.currency}. Мы подтверждаем принятие заказа в соответствии с процессом на
            сайте.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Оплата</h2>
          <p>
            Оплата картой проходит через банк или уполномоченного платёжного партнёра. Вы уполномочиваете
            нас списать выбранный способ оплаты на сумму заказа, включая применимые налоги и сборы при
            их указании.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Самовывоз и доставка</h2>
          <p>
            Варианты получения заказа, слоты и правила передачи описаны на странице{" "}
            <Link href="/delivery-and-refunds" className="underline underline-offset-2">
              Доставка и возвраты
            </Link>
            .
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Ограничение ответственности</h2>
          <p>
            В максимальной степени, разрешённой законом, мы не несём ответственности за косвенный ущерб.
            Ничто в условиях не исключает обязательства, которые нельзя исключить действующим
            потребительским правом.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Применимое право</h2>
          <p>
            Условия регулируются законодательством Грузии. Суды города {SITE_INFO.address.city} имеют
            неисключительную юрисдикцию.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Конфиденциальность</h2>
          <p>
            Подробности в{" "}
            <Link href="/privacy" className="underline underline-offset-2">
              политике конфиденциальности
            </Link>
            .
          </p>
        </section>
      </div>
    </>
  );
}

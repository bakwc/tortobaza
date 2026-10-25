"use client";

import { PayPalButtons, PayPalScriptProvider } from "@paypal/react-paypal-js";
import { useRouter } from "@/i18n/navigation";
import { api } from "@/lib/api";

export function PayPalPayButtons({
  orderNumber,
  lookupToken,
  clientId,
  onPaid,
  onError,
  onCancel,
}: {
  orderNumber: string;
  lookupToken: string;
  clientId: string;
  onPaid: () => void;
  onError: () => void;
  onCancel: () => void;
}) {
  const router = useRouter();

  return (
    <PayPalScriptProvider
      options={{
        clientId,
        currency: "USD",
        intent: "capture",
        components: "buttons",
        enableFunding: "card",
      }}
    >
      <PayPalButtons
        style={{ layout: "vertical" }}
        createOrder={async () => {
          const created = await api.createPayPalOrder({
            number: orderNumber,
            token: lookupToken,
          });
          return created.paypal_order_id;
        }}
        onApprove={async (data) => {
          await api.capturePayPalOrder({
            number: orderNumber,
            token: lookupToken,
            paypal_order_id: data.orderID,
          });
          router.refresh();
          onPaid();
        }}
        onError={() => {
          onError();
        }}
        onCancel={() => {
          onCancel();
        }}
      />
    </PayPalScriptProvider>
  );
}

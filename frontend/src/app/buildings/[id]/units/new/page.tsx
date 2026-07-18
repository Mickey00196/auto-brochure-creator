import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/ui";
import { UnitForm } from "@/components/UnitForm";

export default async function NewUnitPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const building = await api.building(id).catch(() => null);
  if (!building) notFound();

  return (
    <div>
      <PageHeader
        eyebrow={`§5.2 Unit — ${building.name}`}
        title="Add Unit"
        description="Same Unit schema regardless of how the building got here — manual entry or URL import."
      />
      <UnitForm buildingId={id} />
    </div>
  );
}

// The data adapter layer: the ONLY place in the app that imports the raw
// JSON exported from the Python backend (scripts/export_frontend_data.py).
// Every component reads project data through these functions, never by
// importing the JSON files directly — so if the data source ever changes
// (e.g. a real API replaces static JSON), only this file needs to change.

import closeJson from "../data/close.json";
import kpisJson from "../data/kpis.json";
import managementInsightsJson from "../data/management-insights.json";
import metaJson from "../data/meta.json";
import varianceJson from "../data/variance.json";
import type {
  ClosePayload,
  KpisPayload,
  ManagementInsights,
  Meta,
  VariancePayload,
} from "./types";

export function getMeta(): Meta {
  return metaJson as Meta;
}

export function getKpis(): KpisPayload {
  return kpisJson as KpisPayload;
}

export function getManagementInsights(): ManagementInsights {
  return managementInsightsJson as ManagementInsights;
}

export function getVariance(): VariancePayload {
  return varianceJson as VariancePayload;
}

export function getClose(): ClosePayload {
  return closeJson as ClosePayload;
}

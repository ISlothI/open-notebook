{{- define "open-notebook.selector" -}}
app.kubernetes.io/name: open-notebook
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "open-notebook.labels" -}}
{{ include "open-notebook.selector" . }}
app.kubernetes.io/version: {{ .root.Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
helm.sh/chart: {{ .root.Chart.Name }}-{{ .root.Chart.Version }}
{{- end }}

{{- define "open-notebook.podSecurity" -}}
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{- define "open-notebook.containerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: [ALL]
{{- end }}

{{- define "open-notebook.processEnvironment" -}}
- name: ON_ENVIRONMENT
  value: {{ .Values.environment | quote }}
- name: ON_VERSION
  value: {{ .Chart.AppVersion | quote }}
{{- end }}

{{- define "open-notebook.databaseEnvironment" -}}
- name: ON_DATABASE_HOST
  value: {{ .Release.Name }}-database
- name: ON_DATABASE_NAME
  value: open_notebook
- name: ON_DATABASE_USER
  value: open_notebook
- name: ON_DATABASE_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ .Values.databaseSecretName }}
      key: password
- name: ON_EMBEDDER_URL
  value: http://{{ .Release.Name }}-embedder:8001
{{- end }}

{{/* Several pods may start at once: the migration takes an advisory lock. */}}
{{- define "open-notebook.migration" -}}
- name: migrate
  image: {{ .Values.images.backend }}
  command: [alembic, upgrade, head]
  env:
    {{- include "open-notebook.processEnvironment" . | nindent 4 }}
    {{- include "open-notebook.databaseEnvironment" . | nindent 4 }}
  securityContext:
    {{- include "open-notebook.containerSecurity" . | nindent 4 }}
  resources:
    requests: { cpu: 50m, memory: 80Mi }
    limits: { memory: 256Mi }
  volumeMounts:
    - { name: tmp, mountPath: /tmp }
{{- end }}

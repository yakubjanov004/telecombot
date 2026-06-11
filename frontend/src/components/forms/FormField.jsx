export default function FormField({
  label,
  id,
  error,
  children,
  required,
}) {
  return (
    <div className={`form-field ${error ? 'form-field--error' : ''}`}>
      <label className="form-field__label" htmlFor={id}>
        {label}
        {required && <span className="form-field__required" aria-hidden="true"> *</span>}
      </label>
      {children}
      {error && <span className="form-field__error" role="alert">{error}</span>}
    </div>
  );
}

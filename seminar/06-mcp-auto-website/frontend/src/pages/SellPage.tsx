import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SellFormData } from '../types/car';
import { createCarListing } from '../api/cars';
import { carMakes, bodyTypes, fuelTypes, transmissionTypes } from '../data/mockCars';

const TOTAL_STEPS = 4;

const CONDITION_OPTIONS = ['Excellent', 'Very Good', 'Good', 'Fair', 'Poor'];
const FEATURES_OPTIONS = [
  'Navigation System',
  'Backup Camera',
  'Blind Spot Monitor',
  'Apple CarPlay',
  'Android Auto',
  'Heated Seats',
  'Sunroof / Moonroof',
  'Lane Keep Assist',
  'Adaptive Cruise Control',
  'Premium Sound System',
  'Leather Interior',
  'Third Row Seating',
  'Towing Package',
  'All-Wheel Drive',
  'Remote Start',
  'Parking Sensors',
];

const EMPTY_FORM: SellFormData = {
  make: '',
  model: '',
  year: '',
  mileage: '',
  vin: '',
  bodyType: '',
  fuel: '',
  transmission: '',
  condition: '',
  color: '',
  interiorColor: '',
  features: [],
  price: '',
  description: '',
  photos: [],
  sellerName: '',
  sellerEmail: '',
  sellerPhone: '',
  sellerLocation: '',
};

export default function SellPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<SellFormData>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errors, setErrors] = useState<Partial<Record<keyof SellFormData, string>>>({});

  function updateField<K extends keyof SellFormData>(key: K, value: SellFormData[K]) {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function toggleFeature(feature: string) {
    setForm((f) => ({
      ...f,
      features: f.features.includes(feature)
        ? f.features.filter((x) => x !== feature)
        : [...f.features, feature],
    }));
  }

  function validateStep(s: number): boolean {
    const newErrors: typeof errors = {};
    if (s === 1) {
      if (!form.make) newErrors.make = 'Please select a make';
      if (!form.model) newErrors.model = 'Please enter the model';
      if (!form.year) newErrors.year = 'Please enter the year';
      if (!form.mileage) newErrors.mileage = 'Please enter the mileage';
    }
    if (s === 2) {
      if (!form.condition) newErrors.condition = 'Please select condition';
      if (!form.color) newErrors.color = 'Please enter the color';
    }
    if (s === 3) {
      if (!form.price) newErrors.price = 'Please enter the price';
      if (!form.description) newErrors.description = 'Please write a description';
    }
    if (s === 4) {
      if (!form.sellerName) newErrors.sellerName = 'Please enter your name';
      if (!form.sellerEmail) newErrors.sellerEmail = 'Please enter your email';
      if (!form.sellerPhone) newErrors.sellerPhone = 'Please enter your phone';
      if (!form.sellerLocation) newErrors.sellerLocation = 'Please enter your location';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleNext() {
    if (validateStep(step)) setStep((s) => Math.min(TOTAL_STEPS, s + 1));
  }

  function handleBack() {
    setStep((s) => Math.max(1, s - 1));
  }

  async function handleSubmit() {
    if (!validateStep(4)) return;
    setSubmitting(true);
    try {
      await createCarListing({
        make: form.make,
        model: form.model,
        year: Number(form.year),
        mileage: Number(form.mileage),
        price: Number(form.price),
        description: form.description,
        color: form.color,
        features: form.features,
      });
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return <SuccessScreen onBrowse={() => navigate('/cars')} onSellAnother={() => { setForm(EMPTY_FORM); setStep(1); setSubmitted(false); }} />;
  }

  const stepProgress = ((step - 1) / (TOTAL_STEPS - 1)) * 100;

  return (
    <div className="min-h-screen bg-[#12232e] font-lato pt-16">
      {/* Header */}
      <div className="bg-[#0B0C10] border-b border-[#1e3a50] py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-white font-black text-3xl font-lato mb-1">Sell Your Car</h1>
          <p className="text-gray-400 text-sm">Complete the form below to list your vehicle</p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            {STEP_LABELS.map((label, i) => {
              const isActive = step === i + 1;
              const isDone = step > i + 1;
              return (
                <div key={i} className="flex flex-col items-center gap-1.5 flex-1">
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                      isDone
                        ? 'bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white'
                        : isActive
                        ? 'bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white ring-4 ring-[#3a7bd5]/30'
                        : 'bg-[#1a3344] border-2 border-[#1e3a50] text-gray-500'
                    }`}
                  >
                    {isDone ? (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      i + 1
                    )}
                  </div>
                  <span className={`text-xs font-medium hidden sm:block ${isActive || isDone ? 'text-white' : 'text-gray-500'}`}>
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="relative h-1.5 bg-[#1e3a50] rounded-full overflow-hidden">
            <div
              className="absolute h-full bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] rounded-full transition-all duration-500"
              style={{ width: `${stepProgress}%` }}
            />
          </div>
        </div>

        {/* Form card */}
        <div className="bg-[#1a3344] rounded-2xl border border-[#1e3a50] overflow-hidden">
          <div className="p-6 sm:p-8">
            {step === 1 && <Step1 form={form} errors={errors} update={updateField} />}
            {step === 2 && <Step2 form={form} errors={errors} update={updateField} toggleFeature={toggleFeature} />}
            {step === 3 && <Step3 form={form} errors={errors} update={updateField} />}
            {step === 4 && <Step4 form={form} errors={errors} update={updateField} />}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between px-6 sm:px-8 py-4 bg-[#12232e]/40 border-t border-[#1e3a50]">
            <button
              onClick={handleBack}
              disabled={step === 1}
              className="px-6 py-2.5 rounded-lg border border-[#1e3a50] text-gray-300 font-semibold text-sm hover:border-[#3a7bd5] hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Back
            </button>

            <span className="text-gray-500 text-sm">Step {step} of {TOTAL_STEPS}</span>

            {step < TOTAL_STEPS ? (
              <button
                onClick={handleNext}
                className="px-8 py-2.5 rounded-lg bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-bold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-[#3a7bd5]/30"
              >
                Continue
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="px-8 py-2.5 rounded-lg bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-bold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-[#3a7bd5]/30 disabled:opacity-60"
              >
                {submitting ? 'Submitting...' : 'Submit Listing'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const STEP_LABELS = ['Vehicle Info', 'Condition', 'Pricing', 'Contact'];

/* ─── Step Components ─── */

function FormField({
  label,
  required,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-gray-300 mb-1.5">
        {label}
        {required && <span className="text-[#00d2ff] ml-1">*</span>}
      </label>
      {children}
      {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
    </div>
  );
}

const inputClass =
  'w-full bg-[#12232e] border border-[#1e3a50] rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-[#3a7bd5] transition-colors';

const errInputClass =
  'w-full bg-[#12232e] border border-red-500/50 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-red-400 transition-colors';

function Step1({
  form,
  errors,
  update,
}: {
  form: SellFormData;
  errors: Partial<Record<keyof SellFormData, string>>;
  update: <K extends keyof SellFormData>(k: K, v: SellFormData[K]) => void;
}) {
  return (
    <div>
      <h2 className="text-white font-bold text-xl mb-1">Vehicle Information</h2>
      <p className="text-gray-400 text-sm mb-6">Tell us about your vehicle</p>

      <div className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField label="Make" required error={errors.make}>
            <select
              value={form.make}
              onChange={(e) => update('make', e.target.value)}
              className={errors.make ? errInputClass : inputClass}
            >
              <option value="">Select Make</option>
              {carMakes.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </FormField>

          <FormField label="Model" required error={errors.model}>
            <input
              type="text"
              value={form.model}
              onChange={(e) => update('model', e.target.value)}
              placeholder="e.g. 911 Carrera S"
              className={errors.model ? errInputClass : inputClass}
            />
          </FormField>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField label="Year" required error={errors.year}>
            <select
              value={form.year}
              onChange={(e) => update('year', e.target.value)}
              className={errors.year ? errInputClass : inputClass}
            >
              <option value="">Select Year</option>
              {Array.from({ length: 15 }, (_, i) => 2024 - i).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </FormField>

          <FormField label="Mileage" required error={errors.mileage}>
            <input
              type="number"
              value={form.mileage}
              onChange={(e) => update('mileage', e.target.value)}
              placeholder="e.g. 12500"
              min={0}
              className={errors.mileage ? errInputClass : inputClass}
            />
          </FormField>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField label="Body Type">
            <select
              value={form.bodyType}
              onChange={(e) => update('bodyType', e.target.value)}
              className={inputClass}
            >
              <option value="">Select Body Type</option>
              {bodyTypes.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </FormField>

          <FormField label="Fuel Type">
            <select
              value={form.fuel}
              onChange={(e) => update('fuel', e.target.value)}
              className={inputClass}
            >
              <option value="">Select Fuel Type</option>
              {fuelTypes.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </FormField>
        </div>

        <FormField label="Transmission">
          <div className="flex gap-3">
            {transmissionTypes.map((tx) => (
              <button
                key={tx}
                type="button"
                onClick={() => update('transmission', tx)}
                className={`flex-1 py-3 rounded-xl border text-sm font-medium transition-all ${
                  form.transmission === tx
                    ? 'bg-[#3a7bd5]/20 border-[#3a7bd5] text-white'
                    : 'bg-[#12232e] border-[#1e3a50] text-gray-400 hover:border-[#3a7bd5] hover:text-white'
                }`}
              >
                {tx}
              </button>
            ))}
          </div>
        </FormField>

        <FormField label="VIN (Optional)">
          <input
            type="text"
            value={form.vin}
            onChange={(e) => update('vin', e.target.value)}
            placeholder="e.g. 1HGBH41JXMN109186"
            className={inputClass}
          />
        </FormField>
      </div>
    </div>
  );
}

function Step2({
  form,
  errors,
  update,
  toggleFeature,
}: {
  form: SellFormData;
  errors: Partial<Record<keyof SellFormData, string>>;
  update: <K extends keyof SellFormData>(k: K, v: SellFormData[K]) => void;
  toggleFeature: (f: string) => void;
}) {
  return (
    <div>
      <h2 className="text-white font-bold text-xl mb-1">Condition & Features</h2>
      <p className="text-gray-400 text-sm mb-6">Describe the condition and key features</p>

      <div className="space-y-5">
        <FormField label="Condition" required error={errors.condition}>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
            {CONDITION_OPTIONS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => update('condition', c)}
                className={`py-2.5 rounded-xl border text-sm font-medium transition-all ${
                  form.condition === c
                    ? 'bg-[#3a7bd5]/20 border-[#3a7bd5] text-white'
                    : 'bg-[#12232e] border-[#1e3a50] text-gray-400 hover:border-[#3a7bd5] hover:text-white'
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </FormField>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField label="Exterior Color" required error={errors.color}>
            <input
              type="text"
              value={form.color}
              onChange={(e) => update('color', e.target.value)}
              placeholder="e.g. Alpine White"
              className={errors.color ? errInputClass : inputClass}
            />
          </FormField>

          <FormField label="Interior Color">
            <input
              type="text"
              value={form.interiorColor}
              onChange={(e) => update('interiorColor', e.target.value)}
              placeholder="e.g. Black Leather"
              className={inputClass}
            />
          </FormField>
        </div>

        <FormField label="Features">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-1">
            {FEATURES_OPTIONS.map((feature) => {
              const checked = form.features.includes(feature);
              return (
                <button
                  key={feature}
                  type="button"
                  onClick={() => toggleFeature(feature)}
                  className={`flex items-center gap-2 p-2.5 rounded-xl border text-left text-xs transition-all ${
                    checked
                      ? 'bg-[#3a7bd5]/20 border-[#3a7bd5] text-white'
                      : 'bg-[#12232e] border-[#1e3a50] text-gray-400 hover:border-[#3a7bd5] hover:text-white'
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                      checked ? 'bg-[#3a7bd5] border-[#3a7bd5]' : 'border-[#1e3a50]'
                    }`}
                  >
                    {checked && (
                      <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  {feature}
                </button>
              );
            })}
          </div>
        </FormField>
      </div>
    </div>
  );
}

function Step3({
  form,
  errors,
  update,
}: {
  form: SellFormData;
  errors: Partial<Record<keyof SellFormData, string>>;
  update: <K extends keyof SellFormData>(k: K, v: SellFormData[K]) => void;
}) {
  return (
    <div>
      <h2 className="text-white font-bold text-xl mb-1">Pricing & Photos</h2>
      <p className="text-gray-400 text-sm mb-6">Set your asking price and add photos</p>

      <div className="space-y-5">
        <FormField label="Asking Price (USD)" required error={errors.price}>
          <div className="relative">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-semibold">$</span>
            <input
              type="number"
              value={form.price}
              onChange={(e) => update('price', e.target.value)}
              placeholder="e.g. 45000"
              min={0}
              className={`${errors.price ? errInputClass : inputClass} pl-8`}
            />
          </div>
        </FormField>

        <FormField label="Description" required error={errors.description}>
          <textarea
            value={form.description}
            onChange={(e) => update('description', e.target.value)}
            placeholder="Describe your vehicle in detail. Include service history, recent repairs, modifications, and any important information buyers should know..."
            rows={5}
            className={`${errors.description ? errInputClass : inputClass} resize-none`}
          />
          <p className="text-gray-500 text-xs mt-1">{form.description.length} / 1000 characters</p>
        </FormField>

        {/* Photo upload */}
        <FormField label="Photos">
          <div className="border-2 border-dashed border-[#1e3a50] rounded-xl p-8 text-center hover:border-[#3a7bd5]/60 transition-colors cursor-pointer group">
            <div className="w-14 h-14 rounded-2xl bg-[#12232e] border border-[#1e3a50] flex items-center justify-center mx-auto mb-3 group-hover:border-[#3a7bd5]/40 transition-colors">
              <svg className="w-6 h-6 text-gray-500 group-hover:text-[#3a7bd5] transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="text-white font-semibold text-sm mb-1">Drop photos here or click to upload</p>
            <p className="text-gray-400 text-xs">PNG, JPG up to 10MB each. Up to 20 photos.</p>
            <input type="file" accept="image/*" multiple className="hidden" />
          </div>
          <div className="grid grid-cols-4 gap-2 mt-3">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-20 rounded-xl border-2 border-dashed border-[#1e3a50] flex items-center justify-center text-gray-500 text-xs hover:border-[#3a7bd5]/40 transition-colors cursor-pointer"
              >
                +
              </div>
            ))}
          </div>
        </FormField>
      </div>
    </div>
  );
}

function Step4({
  form,
  errors,
  update,
}: {
  form: SellFormData;
  errors: Partial<Record<keyof SellFormData, string>>;
  update: <K extends keyof SellFormData>(k: K, v: SellFormData[K]) => void;
}) {
  return (
    <div>
      <h2 className="text-white font-bold text-xl mb-1">Contact Information</h2>
      <p className="text-gray-400 text-sm mb-6">How buyers can reach you</p>

      <div className="space-y-4">
        <FormField label="Full Name" required error={errors.sellerName}>
          <input
            type="text"
            value={form.sellerName}
            onChange={(e) => update('sellerName', e.target.value)}
            placeholder="John Doe"
            className={errors.sellerName ? errInputClass : inputClass}
          />
        </FormField>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField label="Email Address" required error={errors.sellerEmail}>
            <input
              type="email"
              value={form.sellerEmail}
              onChange={(e) => update('sellerEmail', e.target.value)}
              placeholder="john@example.com"
              className={errors.sellerEmail ? errInputClass : inputClass}
            />
          </FormField>

          <FormField label="Phone Number" required error={errors.sellerPhone}>
            <input
              type="tel"
              value={form.sellerPhone}
              onChange={(e) => update('sellerPhone', e.target.value)}
              placeholder="+1 (555) 000-0000"
              className={errors.sellerPhone ? errInputClass : inputClass}
            />
          </FormField>
        </div>

        <FormField label="Location" required error={errors.sellerLocation}>
          <input
            type="text"
            value={form.sellerLocation}
            onChange={(e) => update('sellerLocation', e.target.value)}
            placeholder="City, State"
            className={errors.sellerLocation ? errInputClass : inputClass}
          />
        </FormField>

        <div className="bg-[#12232e] rounded-xl p-4 border border-[#1e3a50]">
          <div className="flex items-start gap-3">
            <div className="w-5 h-5 rounded-full bg-[#3a7bd5]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-3 h-3 text-[#3a7bd5]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-gray-400 text-xs leading-relaxed">
              By submitting, you agree to our{' '}
              <a href="#" className="text-[#00d2ff] hover:underline">Terms of Service</a>
              {' '}and{' '}
              <a href="#" className="text-[#00d2ff] hover:underline">Privacy Policy</a>.
              Your contact information will only be shared with verified buyers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function SuccessScreen({
  onBrowse,
  onSellAnother,
}: {
  onBrowse: () => void;
  onSellAnother: () => void;
}) {
  return (
    <div className="min-h-screen bg-[#12232e] font-lato flex items-center justify-center pt-16 px-4">
      <div className="max-w-md w-full text-center">
        <div className="relative w-24 h-24 mx-auto mb-6">
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-[#3a7bd5] to-[#00d2ff] opacity-20 animate-ping" />
          <div className="relative w-24 h-24 rounded-full bg-gradient-to-br from-[#3a7bd5] to-[#00d2ff] flex items-center justify-center shadow-2xl shadow-[#3a7bd5]/30">
            <svg className="w-12 h-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>

        <h1 className="text-white font-black text-3xl font-lato mb-3">Listing Submitted!</h1>
        <p className="text-gray-400 leading-relaxed mb-8">
          Your car listing has been submitted successfully. Our team will review it and publish it within 24 hours.
          We'll notify you once it's live.
        </p>

        <div className="bg-[#1a3344] rounded-2xl border border-[#1e3a50] p-5 mb-6 text-left space-y-3">
          <p className="text-white font-semibold text-sm">What happens next?</p>
          {[
            'Your listing is under review (up to 24 hours)',
            'We verify the vehicle information',
            'Your listing goes live to thousands of buyers',
            'Buyers contact you directly',
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="w-5 h-5 rounded-full bg-[#3a7bd5]/20 flex items-center justify-center flex-shrink-0">
                <span className="text-[#3a7bd5] text-xs font-bold">{i + 1}</span>
              </div>
              <span className="text-gray-400 text-sm">{item}</span>
            </div>
          ))}
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={onBrowse}
            className="flex-1 py-3 rounded-xl bg-gradient-to-r from-[#3a7bd5] to-[#00d2ff] text-white font-bold hover:opacity-90 transition-opacity"
          >
            Browse Cars
          </button>
          <button
            onClick={onSellAnother}
            className="flex-1 py-3 rounded-xl bg-[#1a3344] border border-[#1e3a50] text-gray-300 font-bold hover:border-[#3a7bd5] hover:text-white transition-colors"
          >
            Sell Another Car
          </button>
        </div>
      </div>
    </div>
  );
}

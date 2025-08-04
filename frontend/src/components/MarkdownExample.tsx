"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

const markdownExample = `
# 🎉 Markdown Avanzado Funcionando

## Características Soportadas

### 📝 Texto Básico
- **Texto en negrita** y *texto en cursiva*
- ~~Texto tachado~~ y \`código inline\`
- [Enlaces](https://ejemplo.com) con hover effects

### 📋 Listas
1. **Lista numerada**
2. Con múltiples elementos
3. Y sub-elementos

- **Lista con viñetas**
- También funciona
- Con diferentes niveles

### 💻 Bloques de Código
\`\`\`javascript
// Ejemplo de código JavaScript
function saludar(nombre) {
  return \`¡Hola \${nombre}!\`;
}

console.log(saludar("Mundo"));
\`\`\`

\`\`\`python
# Ejemplo de código Python
def calcular_factorial(n):
    if n <= 1:
        return 1
    return n * calcular_factorial(n - 1)

print(calcular_factorial(5))
\`\`\`

### 📊 Tablas
| Característica | Estado | Descripción |
|----------------|--------|-------------|
| **Negrita** | ✅ | Texto en negrita |
| *Cursiva* | ✅ | Texto en cursiva |
| \`Código\` | ✅ | Código inline |
| [Enlaces](https://ejemplo.com) | ✅ | Enlaces clickeables |
| ~~Tachado~~ | ✅ | Texto tachado |

### 💬 Blockquotes
> Este es un blockquote con estilo profesional.
> 
> Puede tener múltiples líneas y se ve muy bien con el borde azul.

### 📏 Líneas Horizontales
---

### ✅ Listas de Tareas
- [x] Instalar react-markdown
- [x] Configurar remark-gfm
- [x] Agregar syntax highlighting
- [x] Personalizar estilos
- [ ] Probar todas las características

### 🔢 Subíndices y Superíndices
- H<sub>2</sub>O (agua)
- E = mc<sup>2</sup> (energía)

### 🎨 Características Avanzadas
- **Colores personalizados** para diferentes elementos
- **Fuente monoespaciada** para código (JetBrains Mono)
- **Syntax highlighting** automático
- **Responsive design** para móviles
- **Animaciones suaves** en hover

---

## 🚀 ¡Listo para usar!

Ahora tu sistema RAG puede mostrar respuestas con markdown completo y se verá profesional.
`;

export default function MarkdownExample() {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed prose-headings:text-gray-900 prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-p:text-gray-700 prose-strong:text-gray-900 prose-code:text-pink-600 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-blockquote:border-l-4 prose-blockquote:border-blue-500 prose-blockquote:pl-4 prose-blockquote:italic prose-ul:list-disc prose-ol:list-decimal">
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeHighlight]}
          components={{
            h1: ({children}) => <h1 className="text-xl font-bold text-gray-900 mb-3">{children}</h1>,
            h2: ({children}) => <h2 className="text-lg font-semibold text-gray-900 mb-2">{children}</h2>,
            h3: ({children}) => <h3 className="text-base font-medium text-gray-900 mb-2">{children}</h3>,
            p: ({children}) => <p className="mb-3 text-gray-700 leading-relaxed">{children}</p>,
            strong: ({children}) => <strong className="font-semibold text-gray-900">{children}</strong>,
            em: ({children}) => <em className="italic text-gray-800">{children}</em>,
            code: ({children, className}) => {
              const isInline = !className;
              if (isInline) {
                return <code className="bg-gray-100 text-pink-600 px-1 py-0.5 rounded text-sm font-mono">{children}</code>;
              }
              return <code className={className}>{children}</code>;
            },
            pre: ({children}) => <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto mb-4">{children}</pre>,
            blockquote: ({children}) => <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-600 mb-4">{children}</blockquote>,
            ul: ({children}) => <ul className="list-disc list-inside mb-4 space-y-1">{children}</ul>,
            ol: ({children}) => <ol className="list-decimal list-inside mb-4 space-y-1">{children}</ol>,
            li: ({children}) => <li className="text-gray-700">{children}</li>,
            a: ({href, children}) => <a href={href} className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer">{children}</a>,
            table: ({children}) => <div className="overflow-x-auto mb-4"><table className="min-w-full border border-gray-300">{children}</table></div>,
            th: ({children}) => <th className="border border-gray-300 bg-gray-100 px-3 py-2 text-left font-semibold">{children}</th>,
            td: ({children}) => <td className="border border-gray-300 px-3 py-2">{children}</td>,
            hr: () => <hr className="border-gray-300 my-4" />
          }}
        >
          {markdownExample}
        </ReactMarkdown>
      </div>
    </div>
  );
} 
from typing import List, Dict, Any
from collections import defaultdict, Counter


class StockAnalyzer:
    """
    Analizador de patrones de stock y disponibilidad de productos.
    """
    
    def analyze_stock_patterns(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analiza patrones generales de stock en todos los productos.
        """
        if not products:
            return {"error": "No products to analyze"}
        
        # Contadores básicos
        total_products = len(products)
        products_with_variants = 0
        total_variants = 0
        in_stock_products = 0
        out_of_stock_products = 0
        
        # Análisis por categoría y marca
        categories = Counter()
        brands = Counter()
        price_ranges = {"under_10": 0, "10_50": 0, "50_100": 0, "over_100": 0}
        
        for product in products:
            # Contar productos con variantes
            variants = product.get("variants", [])
            if variants:
                products_with_variants += 1
                total_variants += len(variants)
                
                # Determinar si está en stock
                has_stock = any(
                    variant.get("in_stock", False) or 
                    variant.get("stock_status") == "in_stock" 
                    for variant in variants
                )
                
                if has_stock:
                    in_stock_products += 1
                else:
                    out_of_stock_products += 1
            
            # Análisis de categorías
            category = product.get("category", "Unknown")
            categories[category] += 1
            
            # Análisis de marcas
            brand = product.get("brand", "Unknown")
            brands[brand] += 1
            
            # Análisis de precios (usar el primer variant como referencia)
            if variants:
                try:
                    price_str = variants[0].get("price", "0")
                    # Extraer número del precio (ej: "$19.99" -> 19.99)
                    price = float(''.join(c for c in str(price_str) if c.isdigit() or c == '.'))
                    
                    if price < 10:
                        price_ranges["under_10"] += 1
                    elif price < 50:
                        price_ranges["10_50"] += 1
                    elif price < 100:
                        price_ranges["50_100"] += 1
                    else:
                        price_ranges["over_100"] += 1
                except (ValueError, TypeError):
                    pass
        
        return {
            "summary": {
                "total_products": total_products,
                "products_with_variants": products_with_variants,
                "total_variants": total_variants,
                "in_stock_products": in_stock_products,
                "out_of_stock_products": out_of_stock_products,
                "stock_percentage": round((in_stock_products / total_products * 100), 2) if total_products > 0 else 0
            },
            "categories": dict(categories.most_common(10)),
            "brands": dict(brands.most_common(10)), 
            "price_distribution": price_ranges
        }
    
    def analyze_availability_by_store(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analiza disponibilidad de productos por tienda/ubicación.
        """
        if not products:
            return {"error": "No products to analyze"}
        
        store_stats = defaultdict(lambda: {
            "total_products": 0,
            "in_stock_products": 0,
            "out_of_stock_products": 0,
            "total_variants": 0,
            "average_variants_per_product": 0,
            "top_categories": Counter(),
            "top_brands": Counter()
        })
        
        for product in products:
            store_id = product.get("store_id", "unknown")
            zipcode = product.get("location_zipcode", "unknown")
            store_key = f"{store_id}_{zipcode}"
            
            stats = store_stats[store_key]
            stats["total_products"] += 1
            
            variants = product.get("variants", [])
            stats["total_variants"] += len(variants)
            
            # Determinar si está en stock
            has_stock = any(
                variant.get("in_stock", False) or 
                variant.get("stock_status") == "in_stock" 
                for variant in variants
            )
            
            if has_stock:
                stats["in_stock_products"] += 1
            else:
                stats["out_of_stock_products"] += 1
            
            # Contar categorías y marcas por tienda
            category = product.get("category", "Unknown")
            stats["top_categories"][category] += 1
            
            brand = product.get("brand", "Unknown")
            stats["top_brands"][brand] += 1
        
        # Procesar estadísticas finales
        processed_stats = {}
        for store_key, stats in store_stats.items():
            total = stats["total_products"]
            processed_stats[store_key] = {
                "total_products": total,
                "in_stock_products": stats["in_stock_products"],
                "out_of_stock_products": stats["out_of_stock_products"],
                "stock_percentage": round((stats["in_stock_products"] / total * 100), 2) if total > 0 else 0,
                "total_variants": stats["total_variants"],
                "average_variants_per_product": round(stats["total_variants"] / total, 2) if total > 0 else 0,
                "top_categories": dict(stats["top_categories"].most_common(5)),
                "top_brands": dict(stats["top_brands"].most_common(5))
            }
        
        return processed_stats
    
    def get_stock_summary(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Obtiene un resumen rápido del estado del stock.
        """
        stock_analysis = self.analyze_stock_patterns(products)
        store_analysis = self.analyze_availability_by_store(products)
        
        return {
            "overall_summary": stock_analysis.get("summary", {}),
            "store_count": len(store_analysis),
            "best_stocked_store": max(
                store_analysis.items(), 
                key=lambda x: x[1]["stock_percentage"]
            ) if store_analysis else None,
            "worst_stocked_store": min(
                store_analysis.items(),
                key=lambda x: x[1]["stock_percentage"]  
            ) if store_analysis else None
        } 
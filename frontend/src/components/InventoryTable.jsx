import React from 'react';
import { AlertTriangle, CheckCircle } from 'lucide-react';

export default function InventoryTable({ items }) {
  if (!items || items.length === 0) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>No inventory records found</div>;
  }

  return (
    <div className="table-container">
      <table className="custom-table">
        <thead>
          <tr>
            <th>SKU / ID</th>
            <th>Product Name</th>
            <th>Category</th>
            <th>Unit Price</th>
            <th>Stock Level</th>
            <th>Reorder Min</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.product_id}>
              <td style={{ fontFamily: 'monospace', fontWeight: 600, color: '#818cf8' }}>{item.product_id}</td>
              <td style={{ fontWeight: 600 }}>{item.product_name}</td>
              <td><span className="badge badge-purple">{item.category}</span></td>
              <td style={{ fontWeight: 600 }}>${item.unit_price.toFixed(2)}</td>
              <td style={{ fontWeight: 700, color: item.needs_reorder ? '#ef4444' : '#10b981' }}>
                {item.stock_level}
              </td>
              <td style={{ color: '#94a3b8' }}>{item.reorder_threshold}</td>
              <td>
                {item.needs_reorder ? (
                  <span className="badge badge-danger" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <AlertTriangle size={12} /> Low Stock
                  </span>
                ) : (
                  <span className="badge badge-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle size={12} /> Optimal
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
